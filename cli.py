#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db, round_time
from src import planner
from src.config import load_config, save_config, get_config, reset_config

RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
PURPLE = '\033[95m'
BOLD = '\033[1m'
END = '\033[0m'


def print_header(text):
    print(f"\n{BOLD}{BLUE}{'=' * 60}{END}")
    print(f"{BOLD}{BLUE}  {text}{END}")
    print(f"{BOLD}{BLUE}{'=' * 60}{END}\n")


def print_menu():
    config = load_config()
    gran = config.get('time_granularity', 0.25)
    print_header(f"排期容量规划工具 (增强版) | 粒度: {gran}小时")
    print(f"{GREEN}1.{END} 技能管理")
    print(f"{GREEN}2.{END} 成员管理")
    print(f"{GREEN}3.{END} 迭代管理")
    print(f"{GREEN}4.{END} 需求管理")
    print(f"{GREEN}5.{END} 依赖管理 (有向+无向环检测)")
    print(f"{GREEN}6.{END} 运行排期规划 (0-1背包算法)")
    print(f"{GREEN}7.{END} 查看规划结果")
    print(f"{GREEN}8.{END} 加载示例数据")
    print(f"{GREEN}9.{END} 系统配置")
    print(f"{GREEN}0.{END} 退出")
    print()


def manage_skills():
    while True:
        print_header("技能管理")
        skills = planner.get_all_skills()
        skill_caps = planner.get_skill_capacity()

        if not skills:
            print(f"{YELLOW}暂无技能{END}\n")
        else:
            print(f"{'ID':<5} {'名称':<20} {'总容量':<10}")
            print("-" * 40)
            for s in skills:
                cap = skill_caps.get(s['id'], {}).get('capacity', 0)
                print(f"{s['id']:<5} {s['name']:<20} {cap:<10.1f} 工时/迭代")
            print()

        print(f"{GREEN}1.{END} 添加技能")
        print(f"{GREEN}2.{END} 删除技能")
        print(f"{GREEN}0.{END} 返回主菜单")
        print()
        choice = input("请选择: ").strip()

        if choice == '1':
            name = input("技能名称 (如: 前端、后端、测试): ").strip()
            planner.add_skill(name)
            print(f"\n{GREEN}技能添加成功！{END}\n")
        elif choice == '2':
            sid = int(input("技能ID: ").strip())
            planner.delete_skill(sid)
            print(f"\n{GREEN}技能删除成功！{END}\n")
        elif choice == '0':
            break


def manage_members():
    while True:
        print_header("成员管理")
        members = planner.get_all_members()
        skills = planner.get_all_skills()
        skill_map = {s['id']: s['name'] for s in skills}

        if not members:
            print(f"{YELLOW}暂无成员{END}\n")
        else:
            for m in members:
                print(f"{BOLD}[{m['id']}]{END} {m['name']} - 总容量: {m['capacity_per_sprint']:.1f} 工时/迭代")
                if m['skills']:
                    skill_strs = [f"{skill_map.get(sk['skill_id'], '?')}: {sk['capacity_per_sprint']:.1f}h"
                                  for sk in m['skills']]
                    print(f"      技能: {', '.join(skill_strs)}")
                else:
                    print(f"      {YELLOW}未设置技能{END}")
            print()

        print(f"{GREEN}1.{END} 添加成员")
        print(f"{GREEN}2.{END} 修改成员")
        print(f"{GREEN}3.{END} 删除成员")
        print(f"{GREEN}4.{END} 设置成员技能")
        print(f"{GREEN}0.{END} 返回主菜单")
        print()
        choice = input("请选择: ").strip()

        if choice == '1':
            name = input("姓名: ").strip()
            gran = get_config('time_granularity', 0.25)
            capacity = float(input(f"每迭代总容量(工时, 支持{gran}小时精度): ").strip())
            planner.add_member(name, capacity)
            print(f"\n{GREEN}成员添加成功！{END}\n")
        elif choice == '2':
            mid = int(input("成员ID: ").strip())
            name = input("新姓名(留空不修改): ").strip() or None
            cap_input = input("新容量(留空不修改): ").strip()
            capacity = float(cap_input) if cap_input else None
            planner.update_member(mid, name, capacity)
            print(f"\n{GREEN}成员更新成功！{END}\n")
        elif choice == '3':
            mid = int(input("成员ID: ").strip())
            planner.delete_member(mid)
            print(f"\n{GREEN}成员删除成功！{END}\n")
        elif choice == '4':
            mid = int(input("成员ID: ").strip())
            print("\n可用技能:")
            for s in skills:
                print(f"  {s['id']}. {s['name']}")
            print()
            sid = int(input("技能ID: ").strip())
            gran = get_config('time_granularity', 0.25)
            cap = float(input(f"该技能每迭代容量(工时, 支持{gran}): ").strip())
            planner.set_member_skill(mid, sid, cap)
            print(f"\n{GREEN}成员技能设置成功！{END}\n")
        elif choice == '0':
            break


def manage_sprints():
    while True:
        print_header("迭代管理")
        sprints = planner.get_all_sprints()
        if not sprints:
            print(f"{YELLOW}暂无迭代{END}\n")
        else:
            print(f"{'ID':<5} {'名称':<20} {'容量':<10} {'开始日期':<12} {'结束日期':<12}")
            print("-" * 65)
            for s in sprints:
                print(f"{s['id']:<5} {s['name']:<20} {s['capacity']:<10.1f} "
                      f"{(s['start_date'] or '-'):<12} {(s['end_date'] or '-'):<12}")
            print()

        print(f"{GREEN}1.{END} 添加迭代")
        print(f"{GREEN}2.{END} 修改迭代")
        print(f"{GREEN}3.{END} 删除迭代")
        print(f"{GREEN}0.{END} 返回主菜单")
        print()
        choice = input("请选择: ").strip()

        if choice == '1':
            name = input("迭代名称: ").strip()
            start = input("开始日期(可选): ").strip() or None
            end = input("结束日期(可选): ").strip() or None
            planner.add_sprint(name, start, end)
            print(f"\n{GREEN}迭代添加成功！{END}\n")
        elif choice == '2':
            sid = int(input("迭代ID: ").strip())
            name = input("新名称(留空不修改): ").strip() or None
            start = input("新开始日期(留空不修改): ").strip() or None
            end = input("新结束日期(留空不修改): ").strip() or None
            if start == '':
                start = None
            if end == '':
                end = None
            planner.update_sprint(sid, name, start, end)
            print(f"\n{GREEN}迭代更新成功！{END}\n")
        elif choice == '3':
            sid = int(input("迭代ID: ").strip())
            planner.delete_sprint(sid)
            print(f"\n{GREEN}迭代删除成功！{END}\n")
        elif choice == '0':
            break


def manage_stories():
    while True:
        print_header("需求管理")
        stories = planner.get_all_stories()
        skills = planner.get_all_skills()
        skill_map = {s['id']: s['name'] for s in skills}

        if not stories:
            print(f"{YELLOW}暂无需{END}\n")
        else:
            print(f"{'ID':<5} {'标题':<25} {'工时':<8} {'优先级':<8} {'排序':<6} {'状态':<12}")
            print("-" * 70)
            for s in stories:
                print(f"{s['id']:<5} {s['title'][:23]:<25} {s['estimate']:<8.1f} "
                      f"{s['priority']:<8} {s['display_order']:<6} {s['status']:<12}")
                if s['skills']:
                    skill_strs = [f"{skill_map.get(sk['skill_id'], '?')}: {sk['required_hours']:.1f}h"
                                  for sk in s['skills']]
                    print(f"      {PURPLE}技能:{END} {', '.join(skill_strs)}")
            print()

        print(f"{GREEN}1.{END} 添加需求")
        print(f"{GREEN}2.{END} 修改需求")
        print(f"{GREEN}3.{END} 删除需求")
        print(f"{GREEN}4.{END} 设置需求技能")
        print(f"{GREEN}5.{END} 调整显示顺序")
        print(f"{GREEN}0.{END} 返回主菜单")
        print()
        choice = input("请选择: ").strip()

        if choice == '1':
            title = input("需求标题: ").strip()
            gran = get_config('time_granularity', 0.25)
            estimate = float(input(f"预估工时(支持{gran}小时精度): ").strip())
            priority = int(input("优先级(数字越大越高): ").strip())
            planner.add_story(title, estimate, priority)
            print(f"\n{GREEN}需求添加成功！{END}\n")
        elif choice == '2':
            sid = int(input("需求ID: ").strip())
            title = input("新标题(留空不修改): ").strip() or None
            est_input = input("新预估工时(留空不修改): ").strip()
            estimate = float(est_input) if est_input else None
            pri_input = input("新优先级(留空不修改): ").strip()
            priority = int(pri_input) if pri_input else None
            planner.update_story(sid, title, estimate, priority)
            print(f"\n{GREEN}需求更新成功！{END}\n")
        elif choice == '3':
            sid = int(input("需求ID: ").strip())
            planner.delete_story(sid)
            print(f"\n{GREEN}需求删除成功！{END}\n")
        elif choice == '4':
            sid = int(input("需求ID: ").strip())
            print("\n可用技能:")
            for s in skills:
                print(f"  {s['id']}. {s['name']}")
            print()
            skill_id = int(input("技能ID: ").strip())
            gran = get_config('time_granularity', 0.25)
            hours = float(input(f"该技能所需工时(支持{gran}): ").strip())
            planner.set_story_skill(sid, skill_id, hours)
            print(f"\n{GREEN}需求技能设置成功！{END}\n")
        elif choice == '5':
            print("\n当前需求顺序 (ID: 标题):")
            for i, s in enumerate(stories):
                print(f"  {i+1}. [{s['id']}] {s['title']}")
            print()
            ordered_input = input("输入新顺序的ID列表，用逗号分隔 (如: 3,1,2): ").strip()
            ordered_ids = [int(x.strip()) for x in ordered_input.split(',')]
            planner.reorder_stories(ordered_ids)
            print(f"\n{GREEN}显示顺序已更新！{END}\n")
        elif choice == '0':
            break


def manage_dependencies():
    while True:
        print_header("依赖管理")
        deps = planner.get_all_dependencies()
        stories = planner.get_all_stories()
        story_map = {s['id']: s['title'] for s in stories}

        cycle = planner.detect_cycle()
        if cycle:
            cycle_type, path = cycle
            type_label = "有向环" if cycle_type == 'directed' else "无向环"
            print(f"{RED}⚠️  警告：检测到{type_label}！路径: {' → '.join(map(str, path))}{END}\n")

        if not deps:
            print(f"{YELLOW}暂无依赖关系{END}\n")
        else:
            print(f"{'ID':<5} {'需求':<30} {'依赖':<30}")
            print("-" * 70)
            for d in deps:
                story_title = story_map.get(d['story_id'], f"#{d['story_id']}")
                dep_title = story_map.get(d['depends_on_id'], f"#{d['depends_on_id']}")
                print(f"{d['id']:<5} {story_title[:28]:<30} 依赖 {dep_title[:28]:<30}")
            print()

        print(f"{GREEN}1.{END} 添加依赖 (自动环检测)")
        print(f"{GREEN}2.{END} 删除依赖")
        print(f"{GREEN}0.{END} 返回主菜单")
        print()
        choice = input("请选择: ").strip()

        if choice == '1':
            story_id = int(input("需求ID: ").strip())
            depends_on_id = int(input("依赖的需求ID: ").strip())
            try:
                planner.add_dependency(story_id, depends_on_id)
                print(f"\n{GREEN}依赖添加成功！{END}\n")
            except ValueError as e:
                print(f"\n{RED}{e}{END}\n")
        elif choice == '2':
            story_id = int(input("需求ID: ").strip())
            depends_on_id = int(input("依赖的需求ID: ").strip())
            planner.remove_dependency(story_id, depends_on_id)
            print(f"\n{GREEN}依赖删除成功！{END}\n")
        elif choice == '0':
            break


def run_planning():
    print_header("运行排期规划 (0-1背包算法)")
    print(f"{YELLOW}使用动态规划0-1背包算法优化容量利用率...{END}")
    print(f"{YELLOW}自动检测: 容量约束 + 技能匹配 + 依赖关系{END}\n")
    try:
        result = planner.run_planning()
        print(f"\n{GREEN}✓ 排期规划完成！(0-1背包算法){END}\n")
        _print_result(result)
    except ValueError as e:
        print(f"\n{RED}✗ 规划失败: {e}{END}\n")


def view_result():
    print_header("规划结果")
    result = planner.get_planning_result()
    _print_result(result)


def _print_result(result):
    if not result:
        print(f"{YELLOW}暂无规划数据，请先添加迭代和需求，然后运行排期规划。{END}\n")
        return

    skill_map = {}
    for item in result:
        for sb in item.get('skill_breakdown', []):
            skill_map[sb['skill_id']] = sb['skill_name']

    for item in result:
        sprint = item['sprint']
        capacity = item['capacity']
        used = item['used']
        stories = item['stories']

        pct = (used / capacity * 100) if capacity > 0 else 0
        status_color = RED if pct > 100 else GREEN

        issue_tag = f" {RED}[有问题]{END}" if item['has_issues'] else ""
        print(f"{BOLD}{sprint['name']}{END}{issue_tag}")
        print(f"  容量: {capacity:.1f} 工时 | 已用: {status_color}{used:.1f}{END} 工时 ({pct:.1f}%)")

        if item.get('skill_breakdown'):
            print(f"  {PURPLE}技能分解:{END}")
            for sb in item['skill_breakdown']:
                sc = sb['capacity']
                su = sb['used']
                spct = (su / sc * 100) if sc > 0 else 0
                sk_color = RED if spct > 100 else GREEN
                print(f"    {sb['skill_name']}: {sk_color}{su:.1f}{END}/{sc:.1f}h ({spct:.0f}%)")
        print()

        if not stories:
            print(f"  {YELLOW}无需求{END}")
        else:
            print(f"  {'ID':<5} {'标题':<30} {'工时':<8} {'优先级':<8} {'状态':<20}")
            print(f"  {'-' * 75}")
            for s in stories:
                status_parts = []
                if s['is_over_capacity']:
                    status_parts.append(f"{RED}超容量{END}")
                if s['is_blocked']:
                    status_parts.append(f"{RED}受阻{END}")
                if s['is_skill_mismatch']:
                    status_parts.append(f"{YELLOW}技能不匹配{END}")
                if not status_parts:
                    status_parts.append(f"{GREEN}正常{END}")
                status_str = " ".join(status_parts)

                is_issue = s['is_over_capacity'] or s['is_blocked'] or s['is_skill_mismatch']
                prefix = f"{RED}!{END} " if is_issue else "  "

                print(f"  {s['id']:<5} {s['title'][:28]:<30} {s['estimate']:<8.1f} "
                      f"{s['priority']:<8} {status_str}")

                if s['dependencies']:
                    dep_titles = [d['title'] for d in s['dependencies']]
                    print(f"        {YELLOW}依赖: {', '.join(dep_titles)}{END}")
                if s.get('skills'):
                    skill_strs = [f"{skill_map.get(sk['skill_id'], '?')}: {sk['required_hours']:.1f}h"
                                  for sk in s['skills']]
                    print(f"        {PURPLE}技能: {', '.join(skill_strs)}{END}")
        print()


def load_sample_data():
    print_header("加载示例数据")

    skills = ["前端", "后端", "测试", "设计"]
    skill_ids = {}
    for name in skills:
        skill_ids[name] = planner.add_skill(name)

    members = [
        ("张三", 40, [("前端", 30), ("设计", 10)]),
        ("李四", 40, [("后端", 40)]),
        ("王五", 32, [("测试", 32)]),
        ("赵六", 40, [("前端", 20), ("后端", 20)]),
    ]
    member_ids = []
    for name, cap, skills_data in members:
        try:
            mid = planner.add_member(name, cap)
            member_ids.append(mid)
            for skill_name, skill_cap in skills_data:
                planner.set_member_skill(mid, skill_ids[skill_name], skill_cap)
        except Exception:
            pass

    sprints = [
        ("Sprint 1", "2026-01-05", "2026-01-16"),
        ("Sprint 2", "2026-01-19", "2026-01-30"),
        ("Sprint 3", "2026-02-02", "2026-02-13"),
    ]
    sprint_ids = []
    for name, start, end in sprints:
        try:
            sid = planner.add_sprint(name, start, end)
            sprint_ids.append(sid)
        except Exception:
            pass

    stories = [
        ("用户登录模块", 16, 10, [("前端", 8), ("后端", 8)]),
        ("用户注册模块", 12, 9, [("前端", 6), ("后端", 6)]),
        ("个人中心页面", 20, 8, [("前端", 12), ("设计", 8)]),
        ("商品列表页", 24, 7, [("前端", 16), ("后端", 8)]),
        ("商品详情页", 16, 6, [("前端", 10), ("后端", 6)]),
        ("购物车功能", 20, 5, [("前端", 8), ("后端", 12)]),
        ("订单系统", 32, 4, [("后端", 24), ("测试", 8)]),
        ("支付集成", 24, 3, [("后端", 16), ("测试", 8)]),
        ("用户评价系统", 16, 2, [("前端", 8), ("后端", 8)]),
        ("消息推送", 12, 1, [("后端", 8), ("测试", 4)]),
    ]
    story_ids = []
    for title, est, pri, skills_data in stories:
        sid = planner.add_story(title, est, pri)
        story_ids.append(sid)
        for skill_name, hours in skills_data:
            planner.set_story_skill(sid, skill_ids[skill_name], hours)

    deps = [
        (2, 1),
        (3, 1),
        (5, 4),
        (6, 5),
        (7, 6),
        (8, 7),
        (9, 3),
        (10, 3),
    ]
    for story_idx, dep_idx in deps:
        try:
            planner.add_dependency(story_ids[story_idx - 1], story_ids[dep_idx - 1])
        except Exception:
            pass

    print(f"\n{GREEN}✓ 示例数据加载成功！{END}")
    print(f"  - 技能: {len(skills)} 种")
    print(f"  - 成员: {len(members)} 人 (含技能分配)")
    print(f"  - 迭代: {len(sprints)} 个")
    print(f"  - 需求: {len(stories)} 个 (含技能需求)")
    print(f"  - 依赖: {len(deps)} 条\n")


def manage_config():
    while True:
        print_header("系统配置")
        config = load_config()
        print("当前配置:")
        print(f"  time_granularity: {config.get('time_granularity')} 小时 (工时粒度)")
        print(f"  knapsack_max_iterations: {config.get('knapsack_max_iterations')} (背包迭代上限因子)")
        print(f"  knapsack_max_items: {config.get('knapsack_max_items')} (单迭代需求上限)")
        print(f"  default_capacity_per_sprint: {config.get('default_capacity_per_sprint')} (默认成员容量)")
        print(f"  reorder_debounce_ms: {config.get('reorder_debounce_ms')} (排序防抖毫秒)")
        print(f"  cycle_detection_undirected: {config.get('cycle_detection_undirected')} (无向环检测)")
        print()
        print(f"{GREEN}1.{END} 修改工时粒度")
        print(f"{GREEN}2.{END} 修改背包迭代上限")
        print(f"{GREEN}3.{END} 修改背包物品上限")
        print(f"{GREEN}4.{END} 开启/关闭无向环检测")
        print(f"{GREEN}5.{END} 重置为默认配置")
        print(f"{GREEN}0.{END} 返回主菜单")
        print()
        choice = input("请选择: ").strip()

        if choice == '1':
            gran = float(input("工时粒度 (推荐: 0.25=15分钟, 0.5=30分钟, 1=1小时): ").strip())
            save_config({'time_granularity': gran})
            print(f"\n{GREEN}工时粒度已改为 {gran} 小时{END}\n")
        elif choice == '2':
            iters = int(input("背包迭代上限因子 (默认100, 越大越精确但越慢): ").strip())
            save_config({'knapsack_max_iterations': iters})
            print(f"\n{GREEN}迭代上限因子已改为 {iters}{END}\n")
        elif choice == '3':
            n = int(input("单迭代需求上限 (默认200, 超则截断): ").strip())
            save_config({'knapsack_max_items': n})
            print(f"\n{GREEN}物品上限已改为 {n}{END}\n")
        elif choice == '4':
            val = input("开启无向环检测? (y/n): ").strip().lower() == 'y'
            save_config({'cycle_detection_undirected': val})
            print(f"\n{GREEN}无向环检测已{'开启' if val else '关闭'}{END}\n")
        elif choice == '5':
            reset_config()
            print(f"\n{GREEN}已重置为默认配置{END}\n")
        elif choice == '0':
            break


def main():
    init_db()

    while True:
        print_menu()
        choice = input("请选择: ").strip()

        if choice == '1':
            manage_skills()
        elif choice == '2':
            manage_members()
        elif choice == '3':
            manage_sprints()
        elif choice == '4':
            manage_stories()
        elif choice == '5':
            manage_dependencies()
        elif choice == '6':
            run_planning()
        elif choice == '7':
            view_result()
        elif choice == '8':
            load_sample_data()
        elif choice == '9':
            manage_config()
        elif choice == '0':
            print(f"\n{GREEN}再见！{END}\n")
            break
        else:
            print(f"\n{RED}无效选择，请重试{END}\n")


if __name__ == '__main__':
    main()
