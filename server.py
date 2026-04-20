from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import requests

load_dotenv()

app = Flask(__name__)

# Configure CORS for your Netlify domain
cors_config = {
    "origins": ["https://defilippi.dev"],
    "methods": ["GET", "POST"],
    "allow_headers": ["Content-Type"]
}
CORS(app, resources={"/api/*": cors_config})

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL')
WORDLE_BOT_URL = os.getenv('WORDLE_BOT_URL', 'http://127.0.0.1:5000')


def get_db_connection():
    """Create a database connection"""
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "Backend healthy"}), 200


# PROJECTS ENDPOINTS
# ============================================================================

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Fetch all active projects from database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute('SELECT * FROM projects WHERE is_active = true ORDER BY id ASC')
        projects = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify([dict(p) for p in projects])

    except Exception as e:
        print(f"Error fetching projects: {e}")
        return jsonify({"error": "Failed to fetch projects"}), 500


@app.route('/api/projects/<slug>', methods=['GET'])
def get_project(slug):
    """Fetch a single project by slug"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            'SELECT * FROM projects WHERE slug = %s AND is_active = true',
            (slug,)
        )
        project = cur.fetchone()

        cur.close()
        conn.close()

        if not project:
            return jsonify({"error": "Project not found"}), 404

        return jsonify(dict(project))

    except Exception as e:
        print(f"Error fetching project: {e}")
        return jsonify({"error": "Failed to fetch project"}), 500


# ML WORDLE IMPLEMENTATIONS
# ============================================================================

@app.route('/api/wordle/play', methods=['POST'])
def wordle_play():
    """Forward Wordle request to the Python bot service"""
    try:
        body = request.json or {}

        # Build query parameters for the Wordle bot
        params = {}
        if 'word' in body:
            params['word'] = body['word']
        if 'model' in body:
            params['model'] = body['model']

        # Call the Wordle bot service
        response = requests.get(
            f"{WORDLE_BOT_URL}/play",
            params=params,
            timeout=35
        )

        if response.status_code != 200:
            return jsonify({"error": "Wordle bot error"}), response.status_code

        return jsonify(response.json())

    except requests.Timeout:
        return jsonify({"error": "Wordle bot request timed out"}), 504
    except Exception as e:
        print(f"Error calling Wordle bot: {e}")
        return jsonify({"error": "Failed to play Wordle"}), 500


@app.route('/api/wordle/models', methods=['GET'])
def wordle_models():
    """Fetch available Wordle bot models"""
    try:
        response = requests.get(f"{WORDLE_BOT_URL}/models", timeout=5)
        return jsonify(response.json()), response.status_code
    except requests.Timeout:
        return jsonify({"success": False, "error": "Could not fetch available models"}), 500
    except Exception as e:
        print(f"[Wordle] FETCH ERROR (before response): {e}")
        return jsonify({"success": False, "error": "Could not fetch available models"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 3000)), debug=False)