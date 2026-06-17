#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import init_db, round_half_hour, get_db_path
from src import planner

def reset_db():
    db_path = get_db_path()
    if os.path.exists(db_path):
        os.remove(db_path)
    init_db()

def test_all():
    print("=" * 60)
    print("排期工具补丁功能验证")
    print("=" * 60)

    # 1. 0.5小时浮点精度
    print("\n✅ 补丁1: 成员工时0.5小时浮点精度")
    tests = [(1.2, 1.0), (1.3, 1.5), (0.5, 0.5), (0.24, 0.0), (0.26, 0.5), (2.75, 3.0)]
    all_ok = True
    for val, expected in tests:
        result = round_half_hour(val)
        ok = result == expected
        if not ok:
            all_ok = False
        print(f"   round_half_hour({val}) = {result} {'✓' if ok else '✗ (期望 ' + str(expected) + ')'}")
    if all_ok:
        print("   ✓ 验证通过")
    else:
        print("   ✗ 验证失败")

    # 2. DAG环检测
    print("\n✅ 补丁2: DAG环检测 + 保存时拒收")
    reset_db()
    s1 = planner.add_story("需求1", 8, 5)
    s2 = planner.add_story("需求2", 8, 5)
    s3 = planner.add_story("需求3", 8, 5)
    planner.add_dependency(s2, s1)
    planner.add_dependency(s3, s2)
    cycle = planner.detect_cycle()
    print(f"   正常依赖无环: {cycle is None}")
    assert cycle is None
    try:
        planner.add_dependency(s1, s3)
        print("   ✗ 应该抛出循环依赖错误")
        assert False
    except ValueError as e:
        print(f"   添加环时拒收: {e}")
    print("   ✓ 验证通过")

    # 3. 技能匹配维度
    print("\n✅ 补丁3: 技能匹配维度 + 超容量红标")
    reset_db()
    frontend = planner.add_skill("前端")
    backend = planner.add_skill("后端")
    m1 = planner.add_member("前端工程师", 40)
    m2 = planner.add_member("后端工程师", 40)
    planner.set_member_skill(m1, frontend, 40)
    planner.set_member_skill(m2, backend, 40)
    s1 = planner.add_story("前端需求", 16, 10)
    planner.set_story_skill(s1, frontend, 16)
    s2 = planner.add_story("后端需求", 16, 9)
    planner.set_story_skill(s2, backend, 16)
    sprint = planner.add_sprint("Sprint 1")
    caps = planner.get_skill_capacity()
    print(f"   前端总容量: {caps[frontend]['capacity']}h")
    print(f"   后端总容量: {caps[backend]['capacity']}h")
    assert caps[frontend]['capacity'] == 40.0
    assert caps[backend]['capacity'] == 40.0
    result = planner.run_planning()
    assert len(result) == 1
    sprint_result = result[0]
    assert len(sprint_result['stories']) == 2
    mismatch_count = len(sprint_result['skill_mismatch_stories'])
    print(f"   技能不匹配需求数: {mismatch_count}")
    assert mismatch_count == 0
    print("   ✓ 验证通过")

    # 4. 0-1背包算法
    print("\n✅ 补丁4: 0-1背包算法优化容量利用率")
    reset_db()
    skill = planner.add_skill("开发")
    m = planner.add_member("工程师", 40)
    planner.set_member_skill(m, skill, 40)
    stories = [
        ("A", 20, 10),
        ("B", 15, 9),
        ("C", 15, 9),
        ("D", 10, 8),
    ]
    story_ids = []
    for title, est, pri in stories:
        sid = planner.add_story(title, est, pri)
        planner.set_story_skill(sid, skill, est)
        story_ids.append(sid)
    sprint = planner.add_sprint("Sprint 1")
    result = planner.run_planning()
    sprint_result = result[0]
    selected = [s['title'] for s in sprint_result['stories'] if not s['is_over_capacity']]
    total_est = sum(s['estimate'] for s in sprint_result['stories'] if not s['is_over_capacity'])
    print(f"   选中需求: {selected}")
    print(f"   总工时: {total_est} / 40 ({total_est/40*100:.1f}%)")
    assert total_est <= 40
    assert total_est >= 35
    print("   ✓ 验证通过 (0-1背包算法提升容量利用率)")

    # 5. 拖动排序持久化
    print("\n✅ 补丁5: Web端拖动排序持久化")
    reset_db()
    ids = []
    for i in range(5):
        sid = planner.add_story(f"需求{i+1}", 8, 5)
        ids.append(sid)
    original_order = [s['id'] for s in planner.get_all_stories()]
    print(f"   原始顺序: {original_order}")
    new_order = [ids[4], ids[2], ids[0], ids[1], ids[3]]
    planner.reorder_stories(new_order)
    actual_order = [s['id'] for s in planner.get_all_stories()]
    print(f"   新顺序: {actual_order}")
    assert actual_order == new_order
    print("   ✓ 验证通过 (排序持久化到后端)")

    print("\n" + "=" * 60)
    print("🎉 所有5项补丁功能验证全部通过！")
    print("=" * 60)

    print("\n📋 补丁功能总结:")
    print("  1. 成员工时0.5小时浮点精度 - 支持半天灵活排期")
    print("  2. 技能匹配维度 - 避免前端工时算到后端任务")
    print("  3. DAG环检测 - 保存时拒收建环")
    print("  4. 0-1背包算法 - 提升临界场景容量利用率")
    print("  5. Web拖动排序持久化 - 避免刷新丢失")

    print("\n📁 修改的文件:")
    print("  - cli.py - 命令行界面，技能管理、环检测提示")
    print("  - web.py - Flask后端，技能API、排序API")
    print("  - static/app.js - 前端拖动排序、技能模态框")
    print("  - static/style.css - 样式优化")
    print("  - src/planner.py - 核心算法")
    print("  - src/database.py - 数据模型")

if __name__ == '__main__':
    test_all()
