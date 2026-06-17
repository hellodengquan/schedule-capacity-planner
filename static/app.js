const API_BASE = '/api';

let members = [];
let sprints = [];
let stories = [];
let dependencies = [];
let planningResult = [];

document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupForms();
    loadAllData();
});

function setupTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(tab).classList.add('active');

            if (tab === 'planning') loadPlanningResult();
            if (tab === 'stories') loadStories();
            if (tab === 'members') loadMembers();
            if (tab === 'sprints') loadSprints();
            if (tab === 'dependencies') {
                loadStories();
                loadDependencies();
            }
        });
    });
}

function setupForms() {
    document.getElementById('story-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const title = document.getElementById('story-title').value;
        const estimate = parseFloat(document.getElementById('story-estimate').value);
        const priority = parseInt(document.getElementById('story-priority').value) || 0;

        await apiPost('/stories', { title, estimate, priority });
        e.target.reset();
        document.getElementById('story-priority').value = '0';
        loadStories();
    });

    document.getElementById('member-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('member-name').value;
        const capacity = parseFloat(document.getElementById('member-capacity').value);

        await apiPost('/members', { name, capacity_per_sprint: capacity });
        e.target.reset();
        document.getElementById('member-capacity').value = '40';
        loadMembers();
    });

    document.getElementById('sprint-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('sprint-name').value;
        const start_date = document.getElementById('sprint-start').value || null;
        const end_date = document.getElementById('sprint-end').value || null;

        await apiPost('/sprints', { name, start_date, end_date });
        e.target.reset();
        loadSprints();
    });

    document.getElementById('dependency-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const story_id = parseInt(document.getElementById('dep-story').value);
        const depends_on_id = parseInt(document.getElementById('dep-depends').value);

        try {
            await apiPost('/dependencies', { story_id, depends_on_id });
            e.target.reset();
            loadDependencies();
        } catch (err) {
            alert('添加失败：' + err.message);
        }
    });
}

async function loadAllData() {
    await Promise.all([
        loadMembers(),
        loadSprints(),
        loadStories(),
        loadPlanningResult()
    ]);
}

async function loadMembers() {
    members = await apiGet('/members');
    renderMembers();
}

async function loadSprints() {
    sprints = await apiGet('/sprints');
    renderSprints();
}

async function loadStories() {
    stories = await apiGet('/stories');
    renderStories();
    updateDependencySelects();
}

async function loadDependencies() {
    dependencies = await apiGet('/dependencies');
    renderDependencies();
}

async function loadPlanningResult() {
    planningResult = await apiGet('/planning/result');
    renderPlanningResult();
}

async function runPlanning() {
    planningResult = await apiPost('/planning/run', {});
    renderPlanningResult();
}

async function loadSampleData() {
    const sampleMembers = [
        ['张三', 40],
        ['李四', 40],
        ['王五', 32],
        ['赵六', 40],
    ];
    for (const [name, cap] of sampleMembers) {
        try {
            await apiPost('/members', { name, capacity_per_sprint: cap });
        } catch (e) {}
    }

    const sampleSprints = [
        ['Sprint 1', '2026-01-05', '2026-01-16'],
        ['Sprint 2', '2026-01-19', '2026-01-30'],
        ['Sprint 3', '2026-02-02', '2026-02-13'],
    ];
    const sprintIds = [];
    for (const [name, start, end] of sampleSprints) {
        try {
            const res = await apiPost('/sprints', { name, start_date: start, end_date: end });
            sprintIds.push(res.id);
        } catch (e) {}
    }

    const sampleStories = [
        ['用户登录模块', 16, 10],
        ['用户注册模块', 12, 9],
        ['个人中心页面', 20, 8],
        ['商品列表页', 24, 7],
        ['商品详情页', 16, 6],
        ['购物车功能', 20, 5],
        ['订单系统', 32, 4],
        ['支付集成', 24, 3],
        ['用户评价系统', 16, 2],
        ['消息推送', 12, 1],
    ];
    const storyIds = [];
    for (const [title, est, pri] of sampleStories) {
        const res = await apiPost('/stories', { title, estimate: est, priority: pri });
        storyIds.push(res.id);
    }

    const deps = [
        [1, 0],
        [2, 0],
        [4, 3],
        [5, 4],
        [6, 5],
        [7, 6],
        [8, 2],
        [9, 2],
    ];
    for (const [si, di] of deps) {
        try {
            await apiPost('/dependencies', { story_id: storyIds[si], depends_on_id: storyIds[di] });
        } catch (e) {}
    }

    loadAllData();
    alert('示例数据加载成功！');
}

function renderMembers() {
    const container = document.getElementById('members-list');
    if (members.length === 0) {
        container.innerHTML = emptyState('👥', '暂无成员');
        return;
    }

    let html = '<table><thead><tr><th>ID</th><th>姓名</th><th>每迭代容量</th><th>操作</th></tr></thead><tbody>';
    members.forEach(m => {
        html += `<tr>
            <td>${m.id}</td>
            <td>${escapeHtml(m.name)}</td>
            <td>${m.capacity_per_sprint} 工时</td>
            <td>
                <button class="btn btn-danger btn-sm" onclick="deleteMember(${m.id})">删除</button>
            </td>
        </tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}

function renderSprints() {
    const container = document.getElementById('sprints-list');
    if (sprints.length === 0) {
        container.innerHTML = emptyState('📅', '暂无迭代');
        return;
    }

    let html = '<table><thead><tr><th>ID</th><th>名称</th><th>容量</th><th>开始日期</th><th>结束日期</th><th>操作</th></tr></thead><tbody>';
    sprints.forEach(s => {
        html += `<tr>
            <td>${s.id}</td>
            <td>${escapeHtml(s.name)}</td>
            <td>${s.capacity} 工时</td>
            <td>${s.start_date || '-'}</td>
            <td>${s.end_date || '-'}</td>
            <td>
                <button class="btn btn-danger btn-sm" onclick="deleteSprint(${s.id})">删除</button>
            </td>
        </tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}

function renderStories() {
    const container = document.getElementById('stories-list');
    if (stories.length === 0) {
        container.innerHTML = emptyState('📝', '暂无需');
        return;
    }

    let html = '<table><thead><tr><th>ID</th><th>标题</th><th>预估工时</th><th>优先级</th><th>状态</th><th>依赖</th><th>操作</th></tr></thead><tbody>';
    stories.forEach(s => {
        const depTitles = s.dependencies ? s.dependencies.map(d => d.title).join(', ') : '-';
        html += `<tr>
            <td>${s.id}</td>
            <td>${escapeHtml(s.title)}</td>
            <td>${s.estimate}</td>
            <td>${s.priority}</td>
            <td>${s.status}</td>
            <td>${escapeHtml(depTitles)}</td>
            <td>
                <button class="btn btn-danger btn-sm" onclick="deleteStory(${s.id})">删除</button>
            </td>
        </tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}

function updateDependencySelects() {
    const storySelect = document.getElementById('dep-story');
    const dependsSelect = document.getElementById('dep-depends');

    const options = stories.map(s => `<option value="${s.id}">${escapeHtml(s.title)}</option>`).join('');
    storySelect.innerHTML = '<option value="">选择需求</option>' + options;
    dependsSelect.innerHTML = '<option value="">选择依赖需求</option>' + options;
}

function renderDependencies() {
    const container = document.getElementById('dependencies-list');
    if (dependencies.length === 0) {
        container.innerHTML = emptyState('🔗', '暂无依赖关系');
        return;
    }

    const storyMap = {};
    stories.forEach(s => storyMap[s.id] = s.title);

    let html = '<table><thead><tr><th>ID</th><th>需求</th><th></th><th>依赖</th><th>操作</th></tr></thead><tbody>';
    dependencies.forEach(d => {
        const storyTitle = storyMap[d.story_id] || `#${d.story_id}`;
        const depTitle = storyMap[d.depends_on_id] || `#${d.depends_on_id}`;
        html += `<tr>
            <td>${d.id}</td>
            <td>${escapeHtml(storyTitle)}</td>
            <td>→ 依赖 →</td>
            <td>${escapeHtml(depTitle)}</td>
            <td>
                <button class="btn btn-danger btn-sm" onclick="removeDependency(${d.story_id}, ${d.depends_on_id})">移除</button>
            </td>
        </tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}

function renderPlanningResult() {
    const container = document.getElementById('planning-result');
    if (planningResult.length === 0) {
        container.innerHTML = emptyState('📊', '暂无规划数据，请先添加迭代和需求，然后点击"运行排期规划"');
        return;
    }

    let html = '';
    planningResult.forEach(item => {
        const sprint = item.sprint;
        const pct = item.capacity > 0 ? (item.used / item.capacity * 100) : 0;
        const isOver = pct > 100;
        const hasIssues = item.has_issues;

        html += `<div class="sprint-card ${hasIssues ? 'has-issues' : ''}">
            <div class="sprint-header">
                <h3>
                    ${escapeHtml(sprint.name)}
                    ${hasIssues ? '<span class="issue-badge">有问题</span>' : ''}
                </h3>
                <div class="capacity-info">
                    容量: ${item.capacity.toFixed(1)} 工时 | 
                    已用: <strong style="color:${isOver ? '#ff4757' : '#52c41a'}">${item.used.toFixed(1)}</strong> 工时 
                    (${pct.toFixed(1)}%)
                </div>
            </div>
            <div class="capacity-bar">
                <div class="capacity-fill ${isOver ? 'over' : ''}" style="width:${Math.min(pct, 100)}%"></div>
            </div>`;

        if (item.stories.length === 0) {
            html += '<p style="color:#999;text-align:center;padding:20px;">无需求</p>';
        } else {
            item.stories.forEach(s => {
                const isOverCap = s.is_over_capacity;
                const isBlocked = s.is_blocked;
                let classes = [];
                if (isOverCap) classes.push('over-capacity');
                if (isBlocked) classes.push('blocked');

                let tags = '';
                if (isOverCap) tags += '<span class="tag tag-over">超容量</span>';
                if (isBlocked) tags += '<span class="tag tag-blocked">受阻</span>';
                tags += `<span class="tag tag-priority">P${s.priority}</span>`;

                let depsHtml = '';
                if (s.dependencies && s.dependencies.length > 0) {
                    const depTitles = s.dependencies.map(d => d.title).join(', ');
                    depsHtml = `<div class="story-deps">🔗 依赖: ${escapeHtml(depTitles)}</div>`;
                }

                html += `<div class="story-item ${classes.join(' ')}">
                    <div class="story-info">
                        <div class="story-title">${escapeHtml(s.title)}</div>
                        <div class="story-meta">预估: ${s.estimate} 工时</div>
                        <div class="story-tags">${tags}</div>
                        ${depsHtml}
                    </div>
                </div>`;
            });
        }

        html += '</div>';
    });

    container.innerHTML = html;
}

function emptyState(icon, text) {
    return `<div class="empty-state">
        <div class="empty-state-icon">${icon}</div>
        <div>${text}</div>
    </div>`;
}

async function deleteMember(id) {
    if (confirm('确定删除该成员吗？')) {
        await apiDelete(`/members/${id}`);
        loadMembers();
    }
}

async function deleteSprint(id) {
    if (confirm('确定删除该迭代吗？')) {
        await apiDelete(`/sprints/${id}`);
        loadSprints();
        loadPlanningResult();
    }
}

async function deleteStory(id) {
    if (confirm('确定删除该需求吗？')) {
        await apiDelete(`/stories/${id}`);
        loadStories();
        loadPlanningResult();
    }
}

async function removeDependency(storyId, dependsOnId) {
    if (confirm('确定移除该依赖关系吗？')) {
        await apiDelete('/dependencies', { story_id: storyId, depends_on_id: dependsOnId });
        loadDependencies();
        loadStories();
    }
}

function refreshPlanning() {
    loadPlanningResult();
}

async function apiGet(path) {
    const res = await fetch(API_BASE + path);
    if (!res.ok) throw new Error('请求失败');
    return res.json();
}

async function apiPost(path, data) {
    const res = await fetch(API_BASE + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ error: '请求失败' }));
        throw new Error(err.error || '请求失败');
    }
    return res.json();
}

async function apiDelete(path, data) {
    const options = { method: 'DELETE' };
    if (data) {
        options.headers = { 'Content-Type': 'application/json' };
        options.body = JSON.stringify(data);
    }
    const res = await fetch(API_BASE + path, options);
    if (!res.ok) throw new Error('请求失败');
    return res.json();
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
