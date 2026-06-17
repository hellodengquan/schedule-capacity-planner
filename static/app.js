const API_BASE = '/api';

let members = [];
let sprints = [];
let stories = [];
let dependencies = [];
let planningResult = [];
let skills = [];

let currentStorySkillId = null;
let currentMemberSkillId = null;
let draggedItem = null;

document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupForms();
    setupDragAndDrop();
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
                checkCycle();
            }
            if (tab === 'skills') loadSkills();
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
        showToast('需求添加成功');
    });

    document.getElementById('member-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('member-name').value;
        const capacity = parseFloat(document.getElementById('member-capacity').value);

        await apiPost('/members', { name, capacity_per_sprint: capacity });
        e.target.reset();
        document.getElementById('member-capacity').value = '40';
        loadMembers();
        showToast('成员添加成功');
    });

    document.getElementById('sprint-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('sprint-name').value;
        const start_date = document.getElementById('sprint-start').value || null;
        const end_date = document.getElementById('sprint-end').value || null;

        await apiPost('/sprints', { name, start_date, end_date });
        e.target.reset();
        loadSprints();
        showToast('迭代添加成功');
    });

    document.getElementById('dependency-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const story_id = parseInt(document.getElementById('dep-story').value);
        const depends_on_id = parseInt(document.getElementById('dep-depends').value);

        try {
            await apiPost('/dependencies', { story_id, depends_on_id });
            e.target.reset();
            loadDependencies();
            checkCycle();
            showToast('依赖添加成功');
        } catch (err) {
            document.getElementById('cycle-warning').textContent = err.message;
            document.getElementById('cycle-warning').classList.remove('hidden');
            setTimeout(() => {
                document.getElementById('cycle-warning').classList.add('hidden');
            }, 3000);
        }
    });

    document.getElementById('skill-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('skill-name').value;
        await apiPost('/skills', { name });
        e.target.reset();
        loadSkills();
        showToast('技能添加成功');
    });

    document.getElementById('story-skill-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const skill_id = parseInt(document.getElementById('story-skill-select').value);
        const required_hours = parseFloat(document.getElementById('story-skill-hours').value) || 0;
        if (!skill_id) return;

        await apiPost(`/stories/${currentStorySkillId}/skills`, { skill_id, required_hours });
        loadStorySkills(currentStorySkillId);
        e.target.reset();
        showToast('技能设置成功');
    });

    document.getElementById('member-skill-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const skill_id = parseInt(document.getElementById('member-skill-select').value);
        const capacity_per_sprint = parseFloat(document.getElementById('member-skill-capacity').value) || 0;
        if (!skill_id) return;

        await apiPost(`/members/${currentMemberSkillId}/skills`, { skill_id, capacity_per_sprint });
        loadMemberSkills(currentMemberSkillId);
        e.target.reset();
        showToast('技能设置成功');
    });
}

function setupDragAndDrop() {
    const list = document.getElementById('stories-list');

    list.addEventListener('dragstart', (e) => {
        if (e.target.classList.contains('story-item-draggable')) {
            draggedItem = e.target;
            e.target.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        }
    });

    list.addEventListener('dragend', (e) => {
        if (e.target.classList.contains('story-item-draggable')) {
            e.target.classList.remove('dragging');
        }
        document.querySelectorAll('.story-item-draggable').forEach(item => {
            item.classList.remove('drag-over');
        });
    });

    list.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';

        const afterElement = getDragAfterElement(list, e.clientY);
        const current = document.querySelector('.dragging');
        if (afterElement == null) {
            list.appendChild(current);
        } else {
            list.insertBefore(current, afterElement);
        }

        document.querySelectorAll('.story-item-draggable').forEach(item => {
            item.classList.remove('drag-over');
        });
        if (afterElement) {
            afterElement.classList.add('drag-over');
        }
    });

    list.addEventListener('drop', async (e) => {
        e.preventDefault();
        const items = list.querySelectorAll('.story-item-draggable');
        const orderedIds = Array.from(items).map(item => parseInt(item.dataset.id));
        try {
            await apiPost('/stories/reorder', { ordered_ids: orderedIds });
            showToast('排序已保存');
        } catch (err) {
            showToast('排序保存失败', true);
            loadStories();
        }
    });
}

function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.story-item-draggable:not(.dragging)')];

    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
            return { offset: offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}

async function loadAllData() {
    await Promise.all([
        loadMembers(),
        loadSprints(),
        loadStories(),
        loadSkills(),
        loadPlanningResult()
    ]);
}

async function loadSkills() {
    skills = await apiGet('/skills');
    renderSkills();
    populateSkillSelects();
}

function populateSkillSelects() {
    const storySelect = document.getElementById('story-skill-select');
    const memberSelect = document.getElementById('member-skill-select');

    storySelect.innerHTML = '<option value="">选择技能</option>';
    memberSelect.innerHTML = '<option value="">选择技能</option>';

    skills.forEach(skill => {
        storySelect.innerHTML += `<option value="${skill.id}">${skill.name}</option>`;
        memberSelect.innerHTML += `<option value="${skill.id}">${skill.name}</option>`;
    });
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
    populateStorySelects();
}

async function loadDependencies() {
    dependencies = await apiGet('/dependencies');
    renderDependencies();
}

async function loadPlanningResult() {
    planningResult = await apiGet('/planning/result');
    renderPlanningResult();
}

async function checkCycle() {
    try {
        const result = await apiGet('/dependencies/check-cycle');
        const warning = document.getElementById('cycle-warning');
        if (result.has_cycle) {
            warning.textContent = `⚠️ 检测到循环依赖：${result.cycle.join(' → ')}`;
            warning.classList.remove('hidden');
        } else {
            warning.classList.add('hidden');
        }
    } catch (e) {
    }
}

async function runPlanning() {
    try {
        planningResult = await apiPost('/planning/run', {});
        renderPlanningResult();
        showToast('排期规划完成 (0-1背包算法)');
    } catch (err) {
        showToast('规划失败: ' + err.message, true);
    }
}

async function loadSampleData() {
    const storiesData = [
        { title: '用户登录模块', estimate: 16, priority: 10 },
        { title: '用户注册模块', estimate: 12, priority: 9 },
        { title: '个人中心页面', estimate: 20, priority: 8 },
        { title: '商品列表页', estimate: 24, priority: 7 },
        { title: '商品详情页', estimate: 16, priority: 6 },
        { title: '购物车功能', estimate: 20, priority: 5 },
        { title: '订单系统', estimate: 32, priority: 4 },
        { title: '支付集成', estimate: 24, priority: 3 },
        { title: '用户评价系统', estimate: 16, priority: 2 },
        { title: '消息推送', estimate: 12, priority: 1 },
    ];

    const membersData = [
        { name: '张三', capacity: 40 },
        { name: '李四', capacity: 40 },
        { name: '王五', capacity: 32 },
        { name: '赵六', capacity: 40 },
    ];

    const sprintsData = [
        { name: 'Sprint 1', start: '2026-01-05', end: '2026-01-16' },
        { name: 'Sprint 2', start: '2026-01-19', end: '2026-01-30' },
        { name: 'Sprint 3', start: '2026-02-02', end: '2026-02-13' },
    ];

    for (const m of membersData) {
        await apiPost('/members', m);
    }
    for (const s of sprintsData) {
        await apiPost('/sprints', { name: s.name, start_date: s.start, end_date: s.end });
    }
    for (const s of storiesData) {
        await apiPost('/stories', s);
    }

    showToast('示例数据加载成功');
    loadAllData();
}

function refreshPlanning() {
    loadPlanningResult();
}

function renderSkills() {
    const container = document.getElementById('skills-list');
    if (skills.length === 0) {
        container.innerHTML = '<p class="empty">暂无技能</p>';
        return;
    }
    container.innerHTML = skills.map(skill => `
        <div class="list-item">
            <div class="item-info">
                <strong>${skill.name}</strong>
            </div>
            <div class="item-actions">
                <button class="btn btn-danger btn-sm" onclick="deleteSkill(${skill.id})">删除</button>
            </div>
        </div>
    `).join('');
}

function renderMembers() {
    const container = document.getElementById('members-list');
    if (members.length === 0) {
        container.innerHTML = '<p class="empty">暂无成员</p>';
        return;
    }
    container.innerHTML = members.map(m => {
        const skillStr = (m.skills || []).map(s => `${s.name}: ${s.capacity_per_sprint}h`).join(', ');
        return `
        <div class="list-item">
            <div class="item-info">
                <strong>${m.name}</strong>
                <span class="badge badge-info">${m.capacity_per_sprint} 工时/迭代</span>
                ${skillStr ? `<span class="skills-mini">技能: ${skillStr}</span>` : ''}
            </div>
            <div class="item-actions">
                <button class="btn btn-secondary btn-sm" onclick="openMemberSkillModal(${m.id}, '${m.name}')">技能</button>
                <button class="btn btn-danger btn-sm" onclick="deleteMember(${m.id})">删除</button>
            </div>
        </div>
    `}).join('');
}

function renderSprints() {
    const container = document.getElementById('sprints-list');
    if (sprints.length === 0) {
        container.innerHTML = '<p class="empty">暂无迭代</p>';
        return;
    }
    container.innerHTML = sprints.map(s => `
        <div class="list-item">
            <div class="item-info">
                <strong>${s.name}</strong>
                <span class="badge badge-info">容量: ${s.capacity}h</span>
                ${s.start_date ? `<span>${s.start_date} ~ ${s.end_date || '-'}</span>` : ''}
            </div>
            <div class="item-actions">
                <button class="btn btn-danger btn-sm" onclick="deleteSprint(${s.id})">删除</button>
            </div>
        </div>
    `).join('');
}

function renderStories() {
    const container = document.getElementById('stories-list');
    if (stories.length === 0) {
        container.innerHTML = '<p class="empty">暂无需</p>';
        return;
    }
    container.innerHTML = stories.map(s => {
        const skillStr = (s.skills || []).map(sk => `${sk.name}: ${sk.required_hours}h`).join(', ');
        return `
        <div class="story-item story-item-draggable" data-id="${s.id}" draggable="true">
            <div class="drag-handle">⋮⋮</div>
            <div class="item-info">
                <strong>${s.title}</strong>
                <span class="badge badge-warning">${s.estimate}h</span>
                <span class="badge badge-primary">优先级: ${s.priority}</span>
                ${skillStr ? `<span class="skills-mini">技能: ${skillStr}</span>` : ''}
            </div>
            <div class="item-actions">
                <button class="btn btn-secondary btn-sm" onclick="openStorySkillModal(${s.id}, '${s.title}')">技能</button>
                <button class="btn btn-danger btn-sm" onclick="deleteStory(${s.id})">删除</button>
            </div>
        </div>
    `}).join('');
}

function renderDependencies() {
    const container = document.getElementById('dependencies-list');
    if (dependencies.length === 0) {
        container.innerHTML = '<p class="empty">暂无依赖</p>';
        return;
    }
    const storyMap = {};
    stories.forEach(s => { storyMap[s.id] = s.title; });

    container.innerHTML = dependencies.map(d => {
        const storyTitle = storyMap[d.story_id] || `#${d.story_id}`;
        const depTitle = storyMap[d.depends_on_id] || `#${d.depends_on_id}`;
        return `
        <div class="list-item">
            <div class="item-info">
                <span>${storyTitle}</span>
                <span class="dep-arrow">→</span>
                <span>${depTitle}</span>
            </div>
            <div class="item-actions">
                <button class="btn btn-danger btn-sm" onclick="removeDependency(${d.story_id}, ${d.depends_on_id})">删除</button>
            </div>
        </div>
    `}).join('');
}

function populateStorySelects() {
    const depStory = document.getElementById('dep-story');
    const depDepends = document.getElementById('dep-depends');
    const options = stories.map(s => `<option value="${s.id}">${s.title}</option>`).join('');
    depStory.innerHTML = '<option value="">选择需求</option>' + options;
    depDepends.innerHTML = '<option value="">选择依赖需求</option>' + options;
}

function renderPlanningResult() {
    const container = document.getElementById('planning-result');
    if (!planningResult || planningResult.length === 0) {
        container.innerHTML = '<div class="card"><p class="empty">暂无规划结果，请点击"运行排期规划"</p></div>';
        return;
    }

    container.innerHTML = planningResult.map(item => {
        const pct = item.capacity > 0 ? (item.used / item.capacity * 100).toFixed(1) : 0;
        const overCap = pct > 100;
        const issueClass = item.has_issues ? 'sprint-issues' : '';

        const storiesHtml = item.stories.map(s => {
            let statusBadges = '';
            let rowClass = '';
            if (s.is_over_capacity) {
                statusBadges += '<span class="badge badge-danger">超容量</span>';
                rowClass = 'story-over-capacity';
            }
            if (s.is_blocked) {
                statusBadges += '<span class="badge badge-danger">受阻</span>';
                rowClass = rowClass || 'story-blocked';
            }
            if (s.is_skill_mismatch) {
                statusBadges += '<span class="badge badge-warning">技能不匹配</span>';
                rowClass = rowClass || 'story-skill-mismatch';
            }
            if (!statusBadges) {
                statusBadges = '<span class="badge badge-success">正常</span>';
            }

            const depStr = (s.dependencies || []).map(d => d.title).join(', ');
            const skillStr = (s.skills || []).map(sk => `${sk.name}: ${sk.required_hours}h`).join(', ');

            return `
                <div class="story-row ${rowClass}">
                    <div class="story-row-title">
                        <strong>${s.title}</strong>
                        <span class="badge badge-info">${s.estimate}h</span>
                        ${statusBadges}
                    </div>
                    ${depStr ? `<div class="story-row-meta">依赖: ${depStr}</div>` : ''}
                    ${skillStr ? `<div class="story-row-meta">技能: ${skillStr}</div>` : ''}
                </div>
            `;
        }).join('');

        const skillBreakdownHtml = (item.skill_breakdown || []).map(sb => {
            const spct = sb.capacity > 0 ? (sb.used / sb.capacity * 100).toFixed(0) : 0;
            const over = sb.used > sb.capacity;
            return `
                <div class="skill-bar">
                    <span class="skill-name">${sb.skill_name}</span>
                    <div class="skill-bar-track">
                        <div class="skill-bar-fill ${over ? 'over' : ''}" style="width: ${Math.min(spct, 100)}%"></div>
                    </div>
                    <span class="skill-hours ${over ? 'over' : ''}">${sb.used}/${sb.capacity}h</span>
                </div>
            `;
        }).join('');

        return `
            <div class="card sprint-card ${issueClass}">
                <div class="sprint-header">
                    <h3>${item.sprint.name} ${item.has_issues ? '<span class="badge badge-danger">有问题</span>' : ''}</h3>
                    <div class="capacity-bar">
                        <div class="capacity-bar-fill ${overCap ? 'over' : ''}" style="width: ${Math.min(pct, 100)}%"></div>
                    </div>
                    <span class="capacity-text ${overCap ? 'over' : ''}">${item.used}/${item.capacity}h (${pct}%)</span>
                </div>
                ${skillBreakdownHtml ? `<div class="skill-breakdown">${skillBreakdownHtml}</div>` : ''}
                <div class="stories-container">
                    ${storiesHtml || '<p class="empty">无需求</p>'}
                </div>
            </div>
        `;
    }).join('');
}

async function deleteSkill(id) {
    if (!confirm('确定删除此技能？')) return;
    await apiDelete(`/skills/${id}`);
    loadSkills();
    showToast('技能已删除');
}

async function deleteMember(id) {
    if (!confirm('确定删除此成员？')) return;
    await apiDelete(`/members/${id}`);
    loadMembers();
    showToast('成员已删除');
}

async function deleteSprint(id) {
    if (!confirm('确定删除此迭代？')) return;
    await apiDelete(`/sprints/${id}`);
    loadSprints();
    showToast('迭代已删除');
}

async function deleteStory(id) {
    if (!confirm('确定删除此需求？')) return;
    await apiDelete(`/stories/${id}`);
    loadStories();
    showToast('需求已删除');
}

async function removeDependency(story_id, depends_on_id) {
    await apiDelete('/dependencies', { story_id, depends_on_id });
    loadDependencies();
    checkCycle();
    showToast('依赖已删除');
}

async function loadStorySkills(storyId) {
    const story = stories.find(s => s.id === storyId);
    if (!story) return;

    const container = document.getElementById('story-skills-list');
    const storySkills = story.skills || [];

    if (storySkills.length === 0) {
        container.innerHTML = '<p class="empty">暂无技能设置</p>';
        return;
    }

    container.innerHTML = storySkills.map(sk => `
        <div class="list-item">
            <div class="item-info">
                <strong>${sk.name}</strong>
                <span class="badge badge-info">${sk.required_hours} 工时</span>
            </div>
            <div class="item-actions">
                <button class="btn btn-danger btn-sm" onclick="removeStorySkill(${storyId}, ${sk.skill_id})">移除</button>
            </div>
        </div>
    `).join('');
}

async function loadMemberSkills(memberId) {
    const member = members.find(m => m.id === memberId);
    if (!member) return;

    const container = document.getElementById('member-skills-list');
    const memberSkills = member.skills || [];

    if (memberSkills.length === 0) {
        container.innerHTML = '<p class="empty">暂无技能设置</p>';
        return;
    }

    container.innerHTML = memberSkills.map(sk => `
        <div class="list-item">
            <div class="item-info">
                <strong>${sk.name}</strong>
                <span class="badge badge-info">${sk.capacity_per_sprint} 工时/迭代</span>
            </div>
            <div class="item-actions">
                <button class="btn btn-danger btn-sm" onclick="removeMemberSkill(${memberId}, ${sk.skill_id})">移除</button>
            </div>
        </div>
    `).join('');
}

async function removeStorySkill(storyId, skillId) {
    await apiDelete(`/stories/${storyId}/skills/${skillId}`);
    const story = stories.find(s => s.id === storyId);
    if (story) {
        story.skills = story.skills.filter(sk => sk.skill_id !== skillId);
    }
    loadStorySkills(storyId);
    showToast('技能已移除');
}

async function removeMemberSkill(memberId, skillId) {
    await apiDelete(`/members/${memberId}/skills/${skillId}`);
    const member = members.find(m => m.id === memberId);
    if (member) {
        member.skills = member.skills.filter(sk => sk.skill_id !== skillId);
    }
    loadMemberSkills(memberId);
    showToast('技能已移除');
}

function openStorySkillModal(storyId, storyTitle) {
    currentStorySkillId = storyId;
    document.querySelector('#story-skill-modal .story-skill-info').textContent = `需求: ${storyTitle}`;
    loadStorySkills(storyId);
    openModal('story-skill-modal');
}

function openMemberSkillModal(memberId, memberName) {
    currentMemberSkillId = memberId;
    document.querySelector('#member-skill-modal .member-skill-info').textContent = `成员: ${memberName}`;
    loadMemberSkills(memberId);
    openModal('member-skill-modal');
}

function openModal(modalId) {
    document.getElementById(modalId).classList.remove('hidden');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
}

function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${isError ? 'error' : ''}`;
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 2000);
}

async function apiGet(path) {
    const res = await fetch(API_BASE + path);
    if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `请求失败 (${res.status})`);
    }
    return res.json();
}

async function apiPost(path, data) {
    const res = await fetch(API_BASE + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `请求失败 (${res.status})`);
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
    if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `请求失败 (${res.status})`);
    }
    return res.json();
}
