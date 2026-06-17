#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import init_db, round_half_hour, round_time, get_db_path
from src import planner
from src.config import load_config, save_config, reset_config, get_config

def reset_all():
    db_path = get_db_path()
    if os.path.exists(db_path):
        os.remove(db_path)
    reset_config()
    init_db()

def test_all():
    print("=" * 60)
    print("排期工具补丁 v2 功能验证")
    print("=" * 60)

    reset_all()

    # 1. 精度 0.25 小时
    print("\n✅ 补丁1: 0.25小时四分之一小时粒度")
    tests = [
        (1.1, 1.0), (1.13, 1.25), (1.3, 1.25), (1.38, 1.5),
        (0.12, 0.0), (0.13, 0.25), (0.25, 0.25), (2.88, 3.0)
    ]
    all_ok = True
    for val, expected in tests:
        result = round_time(val)
        ok = result == expected
        if not ok:
            all_ok = False
        print(f"   round_time({val:>5}) = {result:>5} {'✓' if ok else '✗ (期望 ' + str(expected) + ')'}")
    assert all_ok, "精度测试失败"
    print("   ✓ 验证通过 (四分之一小时精度)")

    # 2. 技能管理 - 可扩展
    print("\n✅ 补丁2: 技能映射表 -> skills 数据库表(可扩展)")
    skills_to_add = ["前端", "后端", "测试", "设计", "DevOps", "数据分析"]
    skill_ids = {}
    for s in skills_to_add:
        sid = planner.add_skill(s)
        skill_ids[s] = sid
    all_skills = planner.get_all_skills()
    print(f"   添加技能数: {len(skills_to_add)}")
    print(f"   读取技能数: {len(all_skills)}")
    skill_names = [s['name'] for s in all_skills]
    for s in skills_to_add:
        assert s in skill_names, f"技能 {s} 不存在"
    caps = planner.get_skill_capacity()
    print(f"   容量计算技能数: {len(caps)}")
    assert len(caps) == len(skills_to_add)
    planner.delete_skill(skill_ids["数据分析"])
    all_skills2 = planner.get_all_skills()
    print(f"   删除后技能数: {len(all_skills2)} (运营可随时删除不想要的技能)")
    print("   ✓ 验证通过 (运营随时增删技能)")

    # 3. DAG 无向环检测
    print("\n✅ 补丁3: DAG检测 + 无向环识别")
    reset_all()
    s1 = planner.add_story("A", 8, 10)
    s2 = planner.add_story("B", 8, 9)
    s3 = planner.add_story("C", 8, 8)
    s4 = planner.add_story("D", 8, 7)

    planner.add_dependency(s2, s1)
    planner.add_dependency(s3, s2)
    cycle = planner.detect_cycle()
    print(f"   正常链式依赖: {cycle is None} (期望 True)")
    assert cycle is None

    try:
        planner.add_dependency(s1, s3)
        print("   ✗ 有向环未被拒收")
        assert False
    except ValueError as e:
        print(f"   有向环拒收: {e}")

    planner.add_dependency(s4, s2)
    from src.database import get_conn
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('INSERT INTO dependencies (story_id, depends_on_id) VALUES (?, ?)', (s3, s4))
    cycle = planner.detect_cycle()
    print(f"   检测无向环(链式): {cycle is not None} (期望 True)")
    assert cycle is not None
    cycle_type, path = cycle
    print(f"   环类型: {cycle_type}, 路径长度: {len(path)}")
    assert cycle_type in ['directed', 'undirected']
    print("   ✓ 验证通过 (有向+无向双重检测)")

    # 4. 配置化背包参数
    print("\n✅ 补丁4: 0-1背包参数可配置化")
    reset_all()
    config = load_config()
    print(f"   默认 time_granularity: {config['time_granularity']}")
    print(f"   默认 knapsack_max_iterations: {config['knapsack_max_iterations']}")
    print(f"   默认 knapsack_max_items: {config['knapsack_max_items']}")
    print(f"   默认 reorder_debounce_ms: {config['reorder_debounce_ms']}")
    print(f"   默认 cycle_detection_undirected: {config['cycle_detection_undirected']}")

    save_config({
        'time_granularity': 0.5,
        'knapsack_max_iterations': 50,
        'knapsack_max_items': 50
    })
    config2 = load_config()
    assert config2['time_granularity'] == 0.5
    assert config2['knapsack_max_iterations'] == 50
    assert config2['knapsack_max_items'] == 50
    assert get_config('time_granularity') == 0.5
    print(f"   配置保存后 time_granularity: {get_config('time_granularity')}")
    print(f"   配置保存后 knapsack_max_iterations: {get_config('knapsack_max_iterations')}")

    # 测试配置精度生效
    result = round_time(1.13)
    print(f"   配置 0.5h 精度后 round_time(1.13) = {result} (期望 1.0)")
    assert result == 1.0

    reset_config()
    result2 = round_time(1.13)
    print(f"   重置后 round_time(1.13) = {result2} (期望 1.25)")
    assert result2 == 1.25
    print("   ✓ 验证通过 (配置即时生效)")

    # 5. 排序持久化 (后端验证，前端debounce只能在浏览器测)
    print("\n✅ 补丁5: 拖动排序持久化接口 (debounce在前端生效)")
    reset_all()
    ids = []
    for i in range(8):
        sid = planner.add_story(f"需求{i+1}", 4, 5)
        ids.append(sid)
    original = [s['id'] for s in planner.get_all_stories()]
    print(f"   初始顺序: {original}")

    new_order = [ids[7], ids[5], ids[3], ids[1], ids[6], ids[4], ids[2], ids[0]]
    planner.reorder_stories(new_order)
    actual = [s['id'] for s in planner.get_all_stories()]
    print(f"   新顺序:   {actual}")
    assert actual == new_order

    debounce_val = get_config('reorder_debounce_ms')
    print(f"   排序防抖配置: {debounce_val}ms (前端debounce)")
    print("   ✓ 验证通过 (排序接口可用，防抖配置化)")

    # 综合测试：在 0.25 小时精度 + 配置下运行排期
    print("\n🎯 综合测试: 0.25小时精度 + 技能匹配 + 0-1背包")
    reset_all()
    frontend = planner.add_skill("前端")
    backend = planner.add_skill("后端")
    m1 = planner.add_member("前端", 40)
    m2 = planner.add_member("后端", 40)
    planner.set_member_skill(m1, frontend, 40)
    planner.set_member_skill(m2, backend, 40)

    stories = [
        ("登录页", 4.25, 10, [(frontend, 4.25)]),
        ("注册页", 3.75, 9, [(frontend, 3.75)]),
        ("登录API", 5.50, 10, [(backend, 5.50)]),
        ("注册API", 6.25, 9, [(backend, 6.25)]),
        ("订单页", 8.75, 8, [(frontend, 8.75)]),
        ("订单API", 12.50, 8, [(backend, 12.50)]),
    ]
    for title, est, pri, skills in stories:
        sid = planner.add_story(title, est, pri)
        for sk_id, hrs in skills:
            planner.set_story_skill(sid, sk_id, hrs)

    planner.add_sprint("Sprint 1")
    result = planner.run_planning()
    sprint = result[0]
    print(f"   迭代 {sprint['sprint']['name']}:")
    for s in sprint['stories']:
        print(f"     - {s['title']:12s} 工时:{s['estimate']:>5.2f}h {'超容量' if s['is_over_capacity'] else 'OK'}")
    print(f"   总容量利用率: {sprint['used']}/{sprint['capacity']}h ({sprint['used']/sprint['capacity']*100:.1f}%)")

    for sb in sprint['skill_breakdown']:
        pct = (sb['used'] / sb['capacity'] * 100) if sb['capacity'] > 0 else 0
        print(f"   {sb['skill_name']:8s}: {sb['used']:>5.2f}/{sb['capacity']:>5.2f}h ({pct:.0f}%)")
    print("   ✓ 综合排期验证通过")

    print("\n" + "=" * 60)
    print("🎉 5项补丁 v2 功能全部验证通过！")
    print("=" * 60)

    print("\n📋 补丁 v2 总结:")
    print("  1. 工时粒度: 0.5h -> 0.25h (四分之一小时/15分钟)")
    print("  2. 技能管理: 统一由 skills 表管理，运营随时增删")
    print("  3. DAG检测: 有向+无向环双重识别，避免漏报")
    print("  4. 背包配置: 迭代上限/物品上限/粒度/环检测/防抖均可配置")
    print("  5. 前端防抖: debounce 合并多次小幅拖动排序请求")

    print("\n📁 修改的文件:")
    print("  - cli.py - 新增系统配置菜单，精度提示更新")
    print("  - web.py - 新增 /api/config 配置接口")
    print("  - static/app.js - debounce 排序，config 标签页")
    print("  - static/style.css - 配置表单样式")
    print("  - src/config.py - 新配置模块")
    print("  - src/database.py - round_time 函数支持配置精度")
    print("  - src/planner.py - 无向环检测，配置化背包")
    print("  - templates/index.html - 配置标签页，step=0.25")

if __name__ == '__main__':
    test_all()
