import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, render_template

from src.database import init_db
from src import planner

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))

init_db()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/members', methods=['GET'])
def list_members():
    return jsonify(planner.get_all_members())


@app.route('/api/members', methods=['POST'])
def create_member():
    data = request.json
    member_id = planner.add_member(data['name'], data['capacity_per_sprint'])
    return jsonify({'id': member_id}), 201


@app.route('/api/members/<int:member_id>', methods=['PUT'])
def update_member(member_id):
    data = request.json
    planner.update_member(
        member_id,
        name=data.get('name'),
        capacity_per_sprint=data.get('capacity_per_sprint')
    )
    return jsonify({'success': True})


@app.route('/api/members/<int:member_id>', methods=['DELETE'])
def delete_member(member_id):
    planner.delete_member(member_id)
    return jsonify({'success': True})


@app.route('/api/sprints', methods=['GET'])
def list_sprints():
    return jsonify(planner.get_all_sprints())


@app.route('/api/sprints', methods=['POST'])
def create_sprint():
    data = request.json
    sprint_id = planner.add_sprint(
        data['name'],
        data.get('start_date'),
        data.get('end_date')
    )
    return jsonify({'id': sprint_id}), 201


@app.route('/api/sprints/<int:sprint_id>', methods=['PUT'])
def update_sprint(sprint_id):
    data = request.json
    planner.update_sprint(
        sprint_id,
        name=data.get('name'),
        start_date=data.get('start_date'),
        end_date=data.get('end_date')
    )
    return jsonify({'success': True})


@app.route('/api/sprints/<int:sprint_id>', methods=['DELETE'])
def delete_sprint(sprint_id):
    planner.delete_sprint(sprint_id)
    return jsonify({'success': True})


@app.route('/api/stories', methods=['GET'])
def list_stories():
    return jsonify(planner.get_all_stories())


@app.route('/api/stories', methods=['POST'])
def create_story():
    data = request.json
    story_id = planner.add_story(
        data['title'],
        data['estimate'],
        data.get('priority', 0)
    )
    return jsonify({'id': story_id}), 201


@app.route('/api/stories/<int:story_id>', methods=['PUT'])
def update_story(story_id):
    data = request.json
    planner.update_story(
        story_id,
        title=data.get('title'),
        estimate=data.get('estimate'),
        priority=data.get('priority'),
        status=data.get('status')
    )
    return jsonify({'success': True})


@app.route('/api/stories/<int:story_id>', methods=['DELETE'])
def delete_story(story_id):
    planner.delete_story(story_id)
    return jsonify({'success': True})


@app.route('/api/dependencies', methods=['GET'])
def list_dependencies():
    return jsonify(planner.get_all_dependencies())


@app.route('/api/dependencies', methods=['POST'])
def create_dependency():
    data = request.json
    try:
        dep_id = planner.add_dependency(data['story_id'], data['depends_on_id'])
        return jsonify({'id': dep_id}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/dependencies', methods=['DELETE'])
def remove_dependency():
    data = request.json
    planner.remove_dependency(data['story_id'], data['depends_on_id'])
    return jsonify({'success': True})


@app.route('/api/planning/run', methods=['POST'])
def run_planning():
    result = planner.run_planning()
    return jsonify(result)


@app.route('/api/planning/result', methods=['GET'])
def get_planning_result():
    return jsonify(planner.get_planning_result())


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
