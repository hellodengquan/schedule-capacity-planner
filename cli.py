#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db
from src import planner


RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
END = '\033[0m'


def print_header(text):
    print(f"\n{BOLD}{BLUE}{'=' * 60}{END}")
    print(f"{BOLD}{BLUE}  {text}{END}")
    print(f"{BOLD}{BLUE}{'=' * 60}{END}\n")


def print_menu():
    print_header("排期容量规划工具")
    print(f"{GREEN}1.{END} 成员管理")
    print(f"{GREEN}2.{END} 迭代管理")
    print(f"{GREEN}3.{END} 需求管理")
    print(f"{GREEN}4.{END} 依赖管理")
    print(f"{GREEN}5.{END} 运行排期规划")
    print(f"{GREEN}6.{END} 查看规划结果")
    print(f"{GREEN}7.{END} 加载示例数据")
    print(f"{GREEN}0.{END} 退出")
    print()


def manage_members():
    while True:
        print_header("成员管理")
        members = planner.get_all_members()
        if not members:
            print(f"{YELLOW}暂无成员{END}\n")
        else:
            print(f"{'ID':<5} {'姓名':<20} {'每迭代容量':<10}")
            print("-" * 40)
            for m in members:
                print(f"{m['id']:<5} {m['name']:<20} {m['capacity_per_sprint']:<10.1f}")
            print()

        print(f"{GREEN}1.{END} 添加成员")
        print(f"{GREEN}2.{END} 修改成员")
        print(f"{GREEN}3.{END} 删除成员")
        print(f"{GREEN}0.{END} 返回主菜单")
        print()
        choice = input("请选择: ").strip()

        if choice == '1':
            name = input("姓名: ").strip()
            capacity = float(input("每迭代容量(工时): ").strip())
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
        if not stories:
            print(f"{YELLOW}暂无需{END}\n")
        else:
            print(f"{'ID':<5} {'标题':<30} {'预估工时':<10} {'优先级':<8} {'状态':<12}")
            print("-" * 70)
            for s in stories:
                print(f"{s['id']:<5} {s['title'][:28]:<30} {s['estimate']:<10.1f} "
                      f"{s['priority']:<8} {s['status']:<12}")
            print()

        print(f"{GREEN}1.{END} 添加需求")
        print(f"{GREEN}2.{END} 修改需求")
        print(f"{GREEN}3.{END} 删除需求")
        print(f"{GREEN}0.{END} 返回主菜单")
        print()
        choice = input("请选择: ").strip()

        if choice == '1':
            title = input("需求标题: ").strip()
            estimate = float(input("预估工时: ").strip())
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
        elif choice == '0':
            break


def manage_dependencies():
    while True:
        print_header("依赖管理")
        deps = planner.get_all_dependencies()
        stories = planner.get_all_stories()
        story_map = {s['id']: s['title'] for s in stories}

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

        print(f"{GREEN}1.{END} 添加依赖")
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
    print_header("运行排期规划")
    result = planner.run_planning()
    print(f"\n{GREEN}排期规划完成！{END}\n")
    _print_result(result)


def view_result():
    print_header("规划结果")
    result = planner.get_planning_result()
    _print_result(result)


def _print_result(result):
    if not result:
        print(f"{YELLOW}暂无规划数据，请先添加迭代和需求，然后运行排期规划。{END}\n")
        return

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
        print()

        if not stories:
            print(f"  {YELLOW}无需求{END}")
        else:
            print(f"  {'ID':<5} {'标题':<30} {'工时':<8} {'优先级':<8} {'状态':<15}")
            print(f"  {'-' * 66}")
            for s in stories:
                status_parts = []
                if s['is_over_capacity']:
                    status_parts.append(f"{RED}超容量{END}")
                if s['is_blocked']:
                    status_parts.append(f"{RED}受阻{END}")
                if not status_parts:
                    status_parts.append(f"{GREEN}正常{END}")
                status_str = " ".join(status_parts)

                is_issue = s['is_over_capacity'] or s['is_blocked']
                prefix = f"{RED}!{END} " if is_issue else "  "

                print(f"  {s['id']:<5} {s['title'][:28]:<30} {s['estimate']:<8.1f} "
                      f"{s['priority']:<8} {status_str}")

                if s['dependencies']:
                    dep_titles = [d['title'] for d in s['dependencies']]
                    print(f"        {YELLOW}依赖: {', '.join(dep_titles)}{END}")
        print()


def load_sample_data():
    print_header("加载示例数据")

    members = [
        ("张三", 40),
        ("李四", 40),
        ("王五", 32),
        ("赵六", 40),
    ]
    for name, cap in members:
        try:
            planner.add_member(name, cap)
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
        ("用户登录模块", 16, 10),
        ("用户注册模块", 12, 9),
        ("个人中心页面", 20, 8),
        ("商品列表页", 24, 7),
        ("商品详情页", 16, 6),
        ("购物车功能", 20, 5),
        ("订单系统", 32, 4),
        ("支付集成", 24, 3),
        ("用户评价系统", 16, 2),
        ("消息推送", 12, 1),
    ]
    story_ids = []
    for title, est, pri in stories:
        sid = planner.add_story(title, est, pri)
        story_ids.append(sid)

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

    print(f"\n{GREEN}示例数据加载成功！{END}")
    print(f"  - 成员: {len(members)} 人")
    print(f"  - 迭代: {len(sprints)} 个")
    print(f"  - 需求: {len(stories)} 个")
    print(f"  - 依赖: {len(deps)} 条\n")


def main():
    init_db()

    while True:
        print_menu()
        choice = input("请选择: ").strip()

        if choice == '1':
            manage_members()
        elif choice == '2':
            manage_sprints()
        elif choice == '3':
            manage_stories()
        elif choice == '4':
            manage_dependencies()
        elif choice == '5':
            run_planning()
        elif choice == '6':
            view_result()
        elif choice == '7':
            load_sample_data()
        elif choice == '0':
            print(f"\n{GREEN}再见！{END}\n")
            break
        else:
            print(f"\n{RED}无效选择，请重试{END}\n")


if __name__ == '__main__':
    main()
