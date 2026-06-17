import sqlite3
from .database import get_conn


def get_sprint_capacity(sprint_id):
    """计算某个迭代的总容量（所有成员容量之和）"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT capacity_per_sprint FROM members')
        rows = c.fetchall()
        total = sum(row['capacity_per_sprint'] for row in rows)
        return total


def get_all_members():
    """获取所有成员"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM members ORDER BY name')
        return [dict(row) for row in c.fetchall()]


def add_member(name, capacity_per_sprint):
    """添加成员"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            'INSERT INTO members (name, capacity_per_sprint) VALUES (?, ?)',
            (name, capacity_per_sprint)
        )
        return c.lastrowid


def update_member(member_id, name=None, capacity_per_sprint=None):
    """更新成员"""
    with get_conn() as conn:
        c = conn.cursor()
        if name is not None:
            c.execute('UPDATE members SET name = ? WHERE id = ?', (name, member_id))
        if capacity_per_sprint is not None:
            c.execute('UPDATE members SET capacity_per_sprint = ? WHERE id = ?',
                      (capacity_per_sprint, member_id))


def delete_member(member_id):
    """删除成员"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM members WHERE id = ?', (member_id,))


def get_all_sprints():
    """获取所有迭代"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM sprints ORDER BY id')
        sprints = [dict(row) for row in c.fetchall()]
        for s in sprints:
            s['capacity'] = get_sprint_capacity(s['id'])
        return sprints


def add_sprint(name, start_date=None, end_date=None):
    """添加迭代"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            'INSERT INTO sprints (name, start_date, end_date) VALUES (?, ?, ?)',
            (name, start_date, end_date)
        )
        return c.lastrowid


def update_sprint(sprint_id, name=None, start_date=None, end_date=None):
    """更新迭代"""
    with get_conn() as conn:
        c = conn.cursor()
        if name is not None:
            c.execute('UPDATE sprints SET name = ? WHERE id = ?', (name, sprint_id))
        if start_date is not None:
            c.execute('UPDATE sprints SET start_date = ? WHERE id = ?', (start_date, sprint_id))
        if end_date is not None:
            c.execute('UPDATE sprints SET end_date = ? WHERE id = ?', (end_date, sprint_id))


def delete_sprint(sprint_id):
    """删除迭代"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM sprint_assignments WHERE sprint_id = ?', (sprint_id,))
        c.execute('UPDATE stories SET sprint_id = NULL WHERE sprint_id = ?', (sprint_id,))
        c.execute('DELETE FROM sprints WHERE id = ?', (sprint_id,))


def get_all_stories():
    """获取所有需求"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM stories ORDER BY priority DESC, id')
        stories = [dict(row) for row in c.fetchall()]
        for story in stories:
            story['dependencies'] = get_story_dependencies(story['id'])
        return stories


def get_story_dependencies(story_id):
    """获取需求的依赖"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT s.* FROM dependencies d
            JOIN stories s ON d.depends_on_id = s.id
            WHERE d.story_id = ?
        ''', (story_id,))
        return [dict(row) for row in c.fetchall()]


def add_story(title, estimate, priority=0):
    """添加需求"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            'INSERT INTO stories (title, estimate, priority) VALUES (?, ?, ?)',
            (title, estimate, priority)
        )
        return c.lastrowid


def update_story(story_id, title=None, estimate=None, priority=None, status=None):
    """更新需求"""
    with get_conn() as conn:
        c = conn.cursor()
        if title is not None:
            c.execute('UPDATE stories SET title = ? WHERE id = ?', (title, story_id))
        if estimate is not None:
            c.execute('UPDATE stories SET estimate = ? WHERE id = ?', (estimate, story_id))
        if priority is not None:
            c.execute('UPDATE stories SET priority = ? WHERE id = ?', (priority, story_id))
        if status is not None:
            c.execute('UPDATE stories SET status = ? WHERE id = ?', (status, story_id))


def delete_story(story_id):
    """删除需求"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM dependencies WHERE story_id = ? OR depends_on_id = ?',
                  (story_id, story_id))
        c.execute('DELETE FROM sprint_assignments WHERE story_id = ?', (story_id,))
        c.execute('DELETE FROM stories WHERE id = ?', (story_id,))


def add_dependency(story_id, depends_on_id):
    """添加依赖关系"""
    if story_id == depends_on_id:
        raise ValueError("需求不能依赖自己")
    with get_conn() as conn:
        c = conn.cursor()
        try:
            c.execute(
                'INSERT INTO dependencies (story_id, depends_on_id) VALUES (?, ?)',
                (story_id, depends_on_id)
            )
        except sqlite3.IntegrityError:
            pass
        return c.lastrowid


def remove_dependency(story_id, depends_on_id):
    """移除依赖关系"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            'DELETE FROM dependencies WHERE story_id = ? AND depends_on_id = ?',
            (story_id, depends_on_id)
        )


def get_all_dependencies():
    """获取所有依赖关系"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM dependencies')
        return [dict(row) for row in c.fetchall()]


def _get_story_with_deps(story_id, cache):
    """递归获取需求及其所有依赖的总工时"""
    if story_id in cache:
        return cache[story_id]
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM stories WHERE id = ?', (story_id,))
        story = dict(c.fetchone())
        c.execute('SELECT depends_on_id FROM dependencies WHERE story_id = ?', (story_id,))
        deps = [row['depends_on_id'] for row in c.fetchall()]
        total = story['estimate']
        for dep_id in deps:
            total += _get_story_with_deps(dep_id, cache)
        cache[story_id] = total
        return total


def _check_dependencies_ready(story_id, assigned_sprint_id, assignments):
    """检查需求的依赖是否都在更早的迭代中完成"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT depends_on_id FROM dependencies WHERE story_id = ?', (story_id,))
        deps = [row['depends_on_id'] for row in c.fetchall()]

    for dep_id in deps:
        dep_assignment = assignments.get(dep_id)
        if dep_assignment is None:
            return False
        if dep_assignment['sprint_id'] >= assigned_sprint_id:
            return False
    return True


def run_planning():
    """
    运行排期规划算法：
    1. 按优先级排序需求
    2. 按迭代顺序依次分配
    3. 检查依赖是否满足
    4. 标记超容量和受阻的需求
    """
    with get_conn() as conn:
        c = conn.cursor()

        c.execute('DELETE FROM sprint_assignments')
        c.execute('UPDATE stories SET sprint_id = NULL, status = ?', ('candidate',))

        c.execute('SELECT * FROM sprints ORDER BY id')
        sprints = [dict(row) for row in c.fetchall()]

        c.execute('SELECT * FROM stories ORDER BY priority DESC, id')
        stories = [dict(row) for row in c.fetchall()]

        if not sprints or not stories:
            return []

        capacity = get_sprint_capacity(sprints[0]['id'])

        sprint_stories = {s['id']: [] for s in sprints}
        sprint_used = {s['id']: 0.0 for s in sprints}
        assignments = {}

        for story in stories:
            assigned = False
            for sprint in sprints:
                sprint_id = sprint['id']

                if not _check_dependencies_ready(story['id'], sprint_id, assignments):
                    continue

                if sprint_used[sprint_id] + story['estimate'] <= capacity:
                    sprint_stories[sprint_id].append(story)
                    sprint_used[sprint_id] += story['estimate']
                    assignments[story['id']] = {
                        'sprint_id': sprint_id,
                        'is_over_capacity': False,
                        'is_blocked': False
                    }
                    assigned = True
                    break

            if not assigned:
                deps_ready = False
                target_sprint = None
                for sprint in sprints:
                    if _check_dependencies_ready(story['id'], sprint['id'], assignments):
                        deps_ready = True
                        target_sprint = sprint['id']
                        break

                if not deps_ready:
                    target_sprint = sprints[-1]['id']
                    is_blocked = True
                    is_over_capacity = False
                else:
                    is_blocked = False
                    is_over_capacity = True

                sprint_stories[target_sprint].append(story)
                assignments[story['id']] = {
                    'sprint_id': target_sprint,
                    'is_over_capacity': is_over_capacity,
                    'is_blocked': is_blocked
                }

        for story_id, assn in assignments.items():
            c.execute('UPDATE stories SET sprint_id = ?, status = ? WHERE id = ?',
                      (assn['sprint_id'], 'assigned', story_id))
            c.execute('''
                INSERT INTO sprint_assignments (story_id, sprint_id, is_over_capacity, is_blocked)
                VALUES (?, ?, ?, ?)
            ''', (story_id, assn['sprint_id'], 1 if assn['is_over_capacity'] else 0,
                  1 if assn['is_blocked'] else 0))

    return get_planning_result()


def get_planning_result():
    """获取规划结果"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM sprints ORDER BY id')
        sprints = [dict(row) for row in c.fetchall()]

        capacity = get_sprint_capacity(sprints[0]['id']) if sprints else 0

        result = []
        for sprint in sprints:
            sprint_id = sprint['id']
            c.execute('''
                SELECT s.*, sa.is_over_capacity, sa.is_blocked
                FROM sprint_assignments sa
                JOIN stories s ON sa.story_id = s.id
                WHERE sa.sprint_id = ?
                ORDER BY s.priority DESC, s.id
            ''', (sprint_id,))
            stories = [dict(row) for row in c.fetchall()]

            used = sum(s['estimate'] for s in stories if not s['is_over_capacity'])
            over_capacity_stories = [s for s in stories if s['is_over_capacity']]
            blocked_stories = [s for s in stories if s['is_blocked']]

            for story in stories:
                c.execute('''
                    SELECT s.* FROM dependencies d
                    JOIN stories s ON d.depends_on_id = s.id
                    WHERE d.story_id = ?
                ''', (story['id'],))
                story['dependencies'] = [dict(row) for row in c.fetchall()]

            result.append({
                'sprint': sprint,
                'capacity': capacity,
                'used': used,
                'stories': stories,
                'over_capacity_stories': over_capacity_stories,
                'blocked_stories': blocked_stories,
                'has_issues': len(over_capacity_stories) > 0 or len(blocked_stories) > 0
            })

        return result
