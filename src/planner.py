import sqlite3
import json
from collections import defaultdict, deque
from .database import get_conn, round_time, round_time
from .config import get_config


def detect_cycle_directed(story_ids, edges):
    """有向环检测（拓扑排序）"""
    graph = defaultdict(list)
    in_degree = defaultdict(int)
    for sid in story_ids:
        in_degree[sid] = 0
    for story_id, depends_on_id in edges:
        graph[depends_on_id].append(story_id)
        in_degree[story_id] += 1

    temp_in_degree = dict(in_degree)
    queue = deque([sid for sid in story_ids if temp_in_degree[sid] == 0])
    visited = 0
    while queue:
        node = queue.popleft()
        visited += 1
        for neighbor in graph[node]:
            temp_in_degree[neighbor] -= 1
            if temp_in_degree[neighbor] == 0:
                queue.append(neighbor)

    if visited != len(story_ids):
        cycle_nodes = [sid for sid in story_ids if temp_in_degree[sid] > 0]
        if cycle_nodes:
            start = cycle_nodes[0]
            path = [start]
            current = start
            guard = 0
            while True:
                guard += 1
                if guard > len(cycle_nodes) * 3:
                    break
                found = False
                for story_id, depends_on_id in edges:
                    if depends_on_id == current and story_id in cycle_nodes:
                        current = story_id
                        path.append(current)
                        found = True
                        break
                if not found:
                    break
                if current == start and len(path) > 1:
                    break
            return ('directed', path)
        return ('directed', True)
    return None


def detect_cycle_undirected(story_ids, edges):
    """无向环检测（DFS），避免漏报"""
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)

    visited = set()
    parent = {}

    def dfs(start):
        stack = [(start, None)]
        path_stack = []
        while stack:
            node, par = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            parent[node] = par
            path_stack.append(node)
            for neighbor in adj[node]:
                if neighbor not in visited:
                    stack.append((neighbor, node))
                elif neighbor != par:
                    cycle = [neighbor]
                    cur = node
                    while cur != neighbor and cur is not None:
                        cycle.append(cur)
                        cur = parent.get(cur)
                    cycle.append(neighbor)
                    return list(reversed(cycle))
        return None

    story_ids_list = list(story_ids)
    for sid in story_ids_list:
        if sid not in visited:
            cycle = dfs(sid)
            if cycle:
                return ('undirected', cycle)
    return None


def detect_cycle():
    """检测依赖图中是否存在环（有向+无向双重检测）"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT id FROM stories')
        story_ids = [row['id'] for row in c.fetchall()]
        c.execute('SELECT story_id, depends_on_id FROM dependencies')
        edges = [(row['story_id'], row['depends_on_id']) for row in c.fetchall()]

    directed_result = detect_cycle_directed(story_ids, edges)
    if directed_result:
        return directed_result

    check_undirected = get_config('cycle_detection_undirected', True)
    if check_undirected:
        undirected_result = detect_cycle_undirected(story_ids, edges)
        if undirected_result:
            return undirected_result

    return None


def check_cycle_if_add(story_id, depends_on_id):
    """检查如果添加这条依赖是否会形成环（有向+无向）"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT story_id, depends_on_id FROM dependencies')
        edges = [(row['story_id'], row['depends_on_id']) for row in c.fetchall()]
        c.execute('SELECT id FROM stories')
        story_ids = {row['id'] for row in c.fetchall()}

    new_edges = edges + [(story_id, depends_on_id)]
    new_story_ids = list(story_ids | {story_id, depends_on_id})

    directed = detect_cycle_directed(new_story_ids, new_edges)
    if directed:
        return True

    check_undirected = get_config('cycle_detection_undirected', True)
    if check_undirected:
        undirected = detect_cycle_undirected(new_story_ids, new_edges)
        if undirected:
            return True

    return False


def get_skill_capacity():
    """获取每个技能的总容量"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT s.id as skill_id, s.name as skill_name,
                   COALESCE(SUM(ms.capacity_per_sprint), 0) as total_capacity
            FROM skills s
            LEFT JOIN member_skills ms ON s.id = ms.skill_id
            GROUP BY s.id, s.name
        ''')
        return {row['skill_id']: {
            'name': row['skill_name'],
            'capacity': round_time(row['total_capacity'])
        } for row in c.fetchall()}


def get_member_skills(member_id):
    """获取成员的技能"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT s.id as skill_id, s.name, ms.capacity_per_sprint
            FROM member_skills ms
            JOIN skills s ON ms.skill_id = s.id
            WHERE ms.member_id = ?
        ''', (member_id,))
        return [dict(row) for row in c.fetchall()]


def get_story_skills(story_id):
    """获取需求需要的技能工时"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT s.id as skill_id, s.name, ss.required_hours
            FROM story_skills ss
            JOIN skills s ON ss.skill_id = s.id
            WHERE ss.story_id = ?
        ''', (story_id,))
        return [dict(row) for row in c.fetchall()]


def get_all_skills():
    """获取所有技能"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM skills ORDER BY name')
        return [dict(row) for row in c.fetchall()]


def add_skill(name):
    """添加技能"""
    with get_conn() as conn:
        c = conn.cursor()
        try:
            c.execute('INSERT INTO skills (name) VALUES (?)', (name,))
            return c.lastrowid
        except sqlite3.IntegrityError:
            c.execute('SELECT id FROM skills WHERE name = ?', (name,))
            return c.fetchone()['id']


def delete_skill(skill_id):
    """删除技能"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM member_skills WHERE skill_id = ?', (skill_id,))
        c.execute('DELETE FROM story_skills WHERE skill_id = ?', (skill_id,))
        c.execute('DELETE FROM skills WHERE id = ?', (skill_id,))


def set_member_skill(member_id, skill_id, capacity_per_sprint):
    """设置成员的技能容量"""
    capacity = round_time(capacity_per_sprint)
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO member_skills (member_id, skill_id, capacity_per_sprint)
            VALUES (?, ?, ?)
            ON CONFLICT(member_id, skill_id) DO UPDATE SET capacity_per_sprint = ?
        ''', (member_id, skill_id, capacity, capacity))


def remove_member_skill(member_id, skill_id):
    """移除成员的技能"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM member_skills WHERE member_id = ? AND skill_id = ?',
                  (member_id, skill_id))


def set_story_skill(story_id, skill_id, required_hours):
    """设置需求需要的技能工时"""
    hours = round_time(required_hours)
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO story_skills (story_id, skill_id, required_hours)
            VALUES (?, ?, ?)
            ON CONFLICT(story_id, skill_id) DO UPDATE SET required_hours = ?
        ''', (story_id, skill_id, hours, hours))


def remove_story_skill(story_id, skill_id):
    """移除需求的技能需求"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM story_skills WHERE story_id = ? AND skill_id = ?',
                  (story_id, skill_id))


def get_sprint_capacity(sprint_id=None):
    """计算某个迭代的总容量（所有成员容量之和）"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT capacity_per_sprint FROM members')
        rows = c.fetchall()
        total = sum(row['capacity_per_sprint'] for row in rows)
        return round_time(total)


def get_all_members():
    """获取所有成员"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM members ORDER BY name')
        members = [dict(row) for row in c.fetchall()]
        for m in members:
            m['capacity_per_sprint'] = round_time(m['capacity_per_sprint'])
            m['skills'] = get_member_skills(m['id'])
        return members


def add_member(name, capacity_per_sprint):
    """添加成员"""
    capacity = round_time(capacity_per_sprint)
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            'INSERT INTO members (name, capacity_per_sprint) VALUES (?, ?)',
            (name, capacity)
        )
        return c.lastrowid


def update_member(member_id, name=None, capacity_per_sprint=None):
    """更新成员"""
    with get_conn() as conn:
        c = conn.cursor()
        if name is not None:
            c.execute('UPDATE members SET name = ? WHERE id = ?', (name, member_id))
        if capacity_per_sprint is not None:
            capacity = round_time(capacity_per_sprint)
            c.execute('UPDATE members SET capacity_per_sprint = ? WHERE id = ?',
                      (capacity, member_id))


def delete_member(member_id):
    """删除成员"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM member_skills WHERE member_id = ?', (member_id,))
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
    """获取所有需求，按display_order排序"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM stories ORDER BY display_order DESC, priority DESC, id')
        stories = [dict(row) for row in c.fetchall()]
        for story in stories:
            story['estimate'] = round_time(story['estimate'])
            story['dependencies'] = get_story_dependencies(story['id'])
            story['skills'] = get_story_skills(story['id'])
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
        deps = [dict(row) for row in c.fetchall()]
        for d in deps:
            d['estimate'] = round_time(d['estimate'])
        return deps


def add_story(title, estimate, priority=0):
    """添加需求"""
    estimate = round_time(estimate)
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT COALESCE(MAX(display_order), 0) + 1 FROM stories')
        display_order = c.fetchone()[0]
        c.execute(
            'INSERT INTO stories (title, estimate, priority, display_order) VALUES (?, ?, ?, ?)',
            (title, estimate, priority, display_order)
        )
        return c.lastrowid


def update_story(story_id, title=None, estimate=None, priority=None, status=None, display_order=None):
    """更新需求"""
    with get_conn() as conn:
        c = conn.cursor()
        if title is not None:
            c.execute('UPDATE stories SET title = ? WHERE id = ?', (title, story_id))
        if estimate is not None:
            est = round_time(estimate)
            c.execute('UPDATE stories SET estimate = ? WHERE id = ?', (est, story_id))
        if priority is not None:
            c.execute('UPDATE stories SET priority = ? WHERE id = ?', (priority, story_id))
        if status is not None:
            c.execute('UPDATE stories SET status = ? WHERE id = ?', (status, story_id))
        if display_order is not None:
            c.execute('UPDATE stories SET display_order = ? WHERE id = ?', (display_order, story_id))


def reorder_stories(ordered_ids):
    """根据ID列表重新设置所有需求的显示顺序"""
    with get_conn() as conn:
        c = conn.cursor()
        for idx, story_id in enumerate(reversed(ordered_ids)):
            c.execute('UPDATE stories SET display_order = ? WHERE id = ?', (idx + 1, story_id))


def delete_story(story_id):
    """删除需求"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM dependencies WHERE story_id = ? OR depends_on_id = ?',
                  (story_id, story_id))
        c.execute('DELETE FROM story_skills WHERE story_id = ?', (story_id,))
        c.execute('DELETE FROM sprint_assignments WHERE story_id = ?', (story_id,))
        c.execute('DELETE FROM stories WHERE id = ?', (story_id,))


def add_dependency(story_id, depends_on_id):
    """添加依赖关系，带环检测"""
    if story_id == depends_on_id:
        raise ValueError("需求不能依赖自己")
    if check_cycle_if_add(story_id, depends_on_id):
        raise ValueError("添加此依赖会形成循环依赖，已拒收")
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


def _knapsack_01(items, capacity, skill_capacities):
    """
    0-1背包算法：在容量约束下选择价值最大的需求组合
    动态规划实现，时间复杂度 O(n * capacity)
    支持配置化精度和迭代上限
    items: [(story, value, weight, skill_weights)]
    capacity: 总容量
    skill_capacities: {skill_id: {name, capacity}}
    返回: (selected_indices, total_value, total_weight, skill_usage)
    """
    n = len(items)
    if n == 0:
        return [], 0, 0, {}

    max_items = int(get_config('knapsack_max_items', 200))
    max_iterations = int(get_config('knapsack_max_iterations', 100))
    granularity = float(get_config('time_granularity', 0.25))
    multiplier = int(1.0 / granularity)

    if n > max_items:
        items_sorted = sorted(items, key=lambda x: x[1], reverse=True)
        items = items_sorted[:max_items]
        n = max_items

    cap_int = int(capacity * multiplier)
    weights_int = [int(item[2] * multiplier) for item in items]

    dp = [-1] * (cap_int + 1)
    dp[0] = 0

    selected_items = [[] for _ in range(cap_int + 1)]
    skill_usage_dp = [defaultdict(float) for _ in range(cap_int + 1)]

    iteration_count = 0
    stop_threshold = max_iterations * 100000

    for i in range(n):
        for w in range(cap_int, -1, -1):
            iteration_count += 1
            if iteration_count > stop_threshold:
                break
            if dp[w] == -1:
                continue
            new_w = w + weights_int[i]
            if new_w > cap_int:
                continue
            current_usage = skill_usage_dp[w].copy()
            skill_ok = True
            for sw in items[i][3]:
                skill_id = sw['skill_id']
                required = sw['required_hours']
                cap = skill_capacities.get(skill_id, {}).get('capacity', 0)
                if current_usage[skill_id] + required > cap:
                    skill_ok = False
                    break
                current_usage[skill_id] += required
            if not skill_ok:
                continue
            new_value = dp[w] + items[i][1]
            if new_value > dp[new_w]:
                dp[new_w] = new_value
                selected_items[new_w] = selected_items[w] + [i]
                skill_usage_dp[new_w] = current_usage
        if iteration_count > stop_threshold:
            break

    best_idx = 0
    for w in range(cap_int + 1):
        if dp[w] > dp[best_idx]:
            best_idx = w

    selected = selected_items[best_idx]
    total_weight = best_idx / multiplier
    skill_usage_final = skill_usage_dp[best_idx]

    return selected, dp[best_idx], total_weight, dict(skill_usage_final)


def _check_skill_feasibility(story_skills, skill_capacities, existing_usage=None):
    """检查需求的技能需求是否能被满足"""
    usage = defaultdict(float)
    if existing_usage:
        usage.update(existing_usage)
    for ss in story_skills:
        skill_id = ss['skill_id']
        required = ss['required_hours']
        cap = skill_capacities.get(skill_id, {}).get('capacity', 0)
        if usage[skill_id] + required > cap:
            return False, usage
        usage[skill_id] += required
    return True, dict(usage)


def run_planning():
    """
    运行排期规划算法（0-1背包优化版）：
    1. 检测是否有循环依赖
    2. 按优先级排序需求
    3. 对每个迭代使用0-1背包算法选择最优需求组合
    4. 检查依赖和技能匹配
    5. 标记超容量、受阻、技能不匹配的需求
    """
    cycle = detect_cycle()
    if cycle:
        cycle_type, path = cycle
        type_label = "有向环" if cycle_type == 'directed' else "无向环"
        raise ValueError(f"检测到{type_label}: {' → '.join(map(str, path))}")

    with get_conn() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM sprint_assignments')
        c.execute('UPDATE stories SET sprint_id = NULL, status = ?', ('candidate',))
        c.execute('SELECT * FROM sprints ORDER BY id')
        sprints = [dict(row) for row in c.fetchall()]
        c.execute('SELECT * FROM stories ORDER BY priority DESC, display_order DESC, id')
        stories = [dict(row) for row in c.fetchall()]

        if not sprints or not stories:
            return []

        capacity = get_sprint_capacity(sprints[0]['id'])
        skill_capacities = get_skill_capacity()

        for s in stories:
            s['estimate'] = round_time(s['estimate'])
            s['skills'] = get_story_skills(s['id'])

        story_map = {s['id']: s for s in stories}
        assignments = {}

        for sprint in sprints:
            sprint_id = sprint['id']
            available_stories = []
            for s in stories:
                if s['id'] in assignments:
                    continue
                if not _check_dependencies_ready(s['id'], sprint_id, assignments):
                    continue
                available_stories.append(s)
            if not available_stories:
                continue

            knapsack_items = []
            for s in available_stories:
                value = s['priority'] * 1000 + (10000 - s['estimate'])
                knapsack_items.append((s, value, s['estimate'], s['skills']))

            selected_indices, total_value, total_weight, skill_usage = _knapsack_01(
                knapsack_items, capacity, skill_capacities
            )

            for idx in selected_indices:
                s = available_stories[idx]
                assignments[s['id']] = {
                    'sprint_id': sprint_id,
                    'is_over_capacity': False,
                    'is_blocked': False,
                    'is_skill_mismatch': False,
                    'skill_breakdown': json.dumps(skill_usage)
                }

        for s in stories:
            if s['id'] in assignments:
                continue
            deps_ready = False
            target_sprint = None
            for sprint in sprints:
                if _check_dependencies_ready(s['id'], sprint['id'], assignments):
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

            skill_ok, _ = _check_skill_feasibility(s['skills'], skill_capacities)
            assignments[s['id']] = {
                'sprint_id': target_sprint,
                'is_over_capacity': is_over_capacity,
                'is_blocked': is_blocked,
                'is_skill_mismatch': not skill_ok,
                'skill_breakdown': None
            }

        for story_id, assn in assignments.items():
            c.execute('UPDATE stories SET sprint_id = ?, status = ? WHERE id = ?',
                      (assn['sprint_id'], 'assigned', story_id))
            c.execute('''
                INSERT INTO sprint_assignments
                (story_id, sprint_id, is_over_capacity, is_blocked, is_skill_mismatch, skill_breakdown)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (story_id, assn['sprint_id'],
                  1 if assn['is_over_capacity'] else 0,
                  1 if assn['is_blocked'] else 0,
                  1 if assn['is_skill_mismatch'] else 0,
                  assn['skill_breakdown']))

    return get_planning_result()


def get_planning_result():
    """获取规划结果"""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM sprints ORDER BY id')
        sprints = [dict(row) for row in c.fetchall()]
        capacity = get_sprint_capacity(sprints[0]['id']) if sprints else 0
        skill_capacities = get_skill_capacity()

        result = []
        for sprint in sprints:
            sprint_id = sprint['id']
            c.execute('''
                SELECT s.*, sa.is_over_capacity, sa.is_blocked,
                       sa.is_skill_mismatch, sa.skill_breakdown
                FROM sprint_assignments sa
                JOIN stories s ON sa.story_id = s.id
                WHERE sa.sprint_id = ?
                ORDER BY s.priority DESC, s.display_order DESC, s.id
            ''', (sprint_id,))
            stories = [dict(row) for row in c.fetchall()]
            for s in stories:
                s['estimate'] = round_time(s['estimate'])
                if s['skill_breakdown']:
                    s['skill_breakdown'] = json.loads(s['skill_breakdown'])

            used = sum(s['estimate'] for s in stories if not s['is_over_capacity'])
            over_capacity_stories = [s for s in stories if s['is_over_capacity']]
            blocked_stories = [s for s in stories if s['is_blocked']]
            skill_mismatch_stories = [s for s in stories if s['is_skill_mismatch']]

            for story in stories:
                c.execute('''
                    SELECT s.* FROM dependencies d
                    JOIN stories s ON d.depends_on_id = s.id
                    WHERE d.story_id = ?
                ''', (story['id'],))
                story['dependencies'] = [dict(row) for row in c.fetchall()]
                story['skills'] = get_story_skills(story['id'])
                for d in story['dependencies']:
                    d['estimate'] = round_time(d['estimate'])

            skill_usage = defaultdict(float)
            for s in stories:
                if not s['is_over_capacity']:
                    for ss in s['skills']:
                        skill_usage[ss['skill_id']] += ss['required_hours']

            skill_breakdown = []
            for skill_id, sc in skill_capacities.items():
                usage = skill_usage.get(skill_id, 0)
                skill_breakdown.append({
                    'skill_id': skill_id,
                    'skill_name': sc['name'],
                    'capacity': sc['capacity'],
                    'used': round_time(usage),
                    'available': round_time(sc['capacity'] - usage)
                })

            result.append({
                'sprint': sprint,
                'capacity': capacity,
                'used': round_time(used),
                'stories': stories,
                'over_capacity_stories': over_capacity_stories,
                'blocked_stories': blocked_stories,
                'skill_mismatch_stories': skill_mismatch_stories,
                'skill_breakdown': skill_breakdown,
                'has_issues': (len(over_capacity_stories) > 0 or
                               len(blocked_stories) > 0 or
                               len(skill_mismatch_stories) > 0)
            })
        return result
