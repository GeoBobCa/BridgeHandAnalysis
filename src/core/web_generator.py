import os
import json
import urllib.parse
from jinja2 import Environment, FileSystemLoader

# CONFIGURATION
JSON_FOLDER = "data/session_results"
OUTPUT_HTML_FOLDER = "docs"
TEMPLATE_DIR = "src/templates"

class WebGenerator:
    def __init__(self):
        os.makedirs(OUTPUT_HTML_FOLDER, exist_ok=True)
        os.makedirs(TEMPLATE_DIR, exist_ok=True)
        self.env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        self._create_default_templates()

    def generate_all(self):
        files = [f for f in os.listdir(JSON_FOLDER) if f.endswith(".json")]
        hands_data = []
        
        for f in files:
            with open(os.path.join(JSON_FOLDER, f), 'r', encoding='utf-8') as json_file:
                hands_data.append(json.load(json_file))
        
        try:
            hands_data.sort(key=lambda x: int(x['facts']['board'].replace('Board ', '')))
        except ValueError:
            pass 

        self._render_page("index.html", "index.html", hands=hands_data)
        
        for hand in hands_data:
            safe_filename = hand['facts']['board'].replace(' ', '_') + ".html"
            hand['handviewer_url'] = "http://www.bridgebase.com/tools/handviewer.html?lin=" + \
                                     urllib.parse.quote(hand['facts']['raw_lin'])
            self._render_page("hand_detail.html", safe_filename, hand=hand)
            
        print(f"Website generated in: {OUTPUT_HTML_FOLDER}/")

    def _render_page(self, template_name, output_filename, **kwargs):
        template = self.env.get_template(template_name)
        html_content = template.render(**kwargs)
        with open(os.path.join(OUTPUT_HTML_FOLDER, output_filename), 'w', encoding='utf-8') as f:
            f.write(html_content)

    def _create_default_templates(self):
        # 1. DASHBOARD
        index_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Bridge Session Report</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <style>
                .player-names { font-size: 0.85em; color: #555; }
            </style>
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <h1 class="mb-4">Bridge Session Analysis</h1>
                <div class="row">
                    {% for item in hands %}
                    <div class="col-md-4 mb-4">
                        <div class="card h-100 shadow-sm">
                            <div class="card-header d-flex justify-content-between align-items-center">
                                <strong>{{ item.facts.board }}</strong>
                                <span class="badge bg-primary">{{ item.facts.vulnerability }}</span>
                            </div>
                            <div class="card-body">
                                <h5 class="card-title">{{ item.ai_analysis.verdict }}</h5>
                                <div class="player-names mb-3 border-top border-bottom py-2">
                                    <div><strong>N/S:</strong> {{ item.facts.hands.North.name }} & {{ item.facts.hands.South.name }}</div>
                                    <div><strong>E/W:</strong> {{ item.facts.hands.East.name }} & {{ item.facts.hands.West.name }}</div>
                                </div>
                                <p class="card-text small text-muted">
                                    Dealer: {{ item.facts.dealer }}
                                </p>
                                <a href="{{ item.facts.board | replace(' ', '_') }}.html" class="btn btn-outline-primary w-100">View Analysis</a>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </body>
        </html>
        """
        
        # 2. DETAIL PAGE
        detail_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{{ hand.facts.board }} - Analysis</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <style>
                .coach-box { background-color: #e8f4f8; border-left: 5px solid #007bff; }
                .player-name { font-size: 0.9em; color: #666; font-style: italic; }
            </style>
        </head>
        <body class="bg-light">
            <div class="container py-4">
                <div class="d-flex justify-content-between mb-3">
                    <a href="index.html" class="btn btn-secondary">&larr; Back to Dashboard</a>
                    <a href="{{ hand.handviewer_url }}" target="_blank" class="btn btn-danger">
                        ▶ Replay Hand (BBO)
                    </a>
                </div>
                
                <div class="card mb-4 shadow-sm">
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-8">
                                <h2 class="display-6">{{ hand.facts.board }}</h2>
                                <h4 class="text-muted">{{ hand.ai_analysis.verdict }}</h4>
                            </div>
                            <div class="col-md-4 text-end">
                                <span class="badge bg-secondary">Dealer: {{ hand.facts.dealer }}</span>
                                <span class="badge bg-warning text-dark">Vul: {{ hand.facts.vulnerability }}</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row mb-4">
                    <div class="col-md-6">
                        <div class="card h-100">
                            <div class="card-header bg-dark text-white">The Deal (Verified)</div>
                            <div class="card-body">
                                <div class="row text-center align-items-center">
                                    <div class="col-12 mb-3">
                                        <div class="player-name">{{ hand.facts.hands.North.name }}</div>
                                        <strong>North ({{ hand.facts.hands.North.stats.hcp }} HCP)</strong><br>
                                        {{ hand.facts.hands.North.stats.distribution_str }}
                                    </div>
                                    <div class="col-3">
                                        <div class="player-name">{{ hand.facts.hands.West.name }}</div>
                                        <strong>West</strong><br>
                                        {{ hand.facts.hands.West.stats.hcp }} HCP
                                    </div>
                                    <div class="col-6">
                                        <img src="https://bridgebase.com/mobile/images/table_felt.jpg" class="img-fluid rounded shadow-sm" style="opacity:0.5">
                                    </div>
                                    <div class="col-3">
                                        <div class="player-name">{{ hand.facts.hands.East.name }}</div>
                                        <strong>East</strong><br>
                                        {{ hand.facts.hands.East.stats.hcp }} HCP
                                    </div>
                                    <div class="col-12 mt-3">
                                        <div class="player-name">{{ hand.facts.hands.South.name }}</div>
                                        <strong>South ({{ hand.facts.hands.South.stats.hcp }} HCP)</strong><br>
                                        {{ hand.facts.hands.South.stats.distribution_str }}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card h-100">
                            <div class="card-header bg-dark text-white">Auction History</div>
                            <div class="card-body font-monospace d-flex align-items-center justify-content-center">
                                <div class="p-3 bg-light rounded border w-100 text-center">
                                    {{ hand.facts.auction | join(' - ') }}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="card mb-3">
                    <div class="card-header bg-success text-white">Audrey's Analysis</div>
                    <div class="card-body">
                        <h5>Standard American Critique</h5>
                        <p>{{ hand.ai_analysis.basic_analysis }}</p>
                        <hr>
                        <button class="btn btn-outline-dark btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#advancedBox">
                            🎓 Toggle Advanced Analysis
                        </button>
                        <div class="collapse mt-3" id="advancedBox">
                            <div class="card card-body bg-light border-warning">
                                <strong>Advanced Insight:</strong>
                                {{ hand.ai_analysis.advanced_insight }}
                            </div>
                        </div>
                    </div>
                </div>

                {% if hand.ai_analysis.lesson_module %}
                <div class="card coach-box mb-5">
                    <div class="card-body">
                        <h4 class="text-primary">💡 Coach's Corner: {{ hand.ai_analysis.lesson_module.topic }}</h4>
                        <p>{{ hand.ai_analysis.lesson_module.content }}</p>
                    </div>
                </div>
                {% endif %}

            </div>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """

        # Force overwrite to ensure new format
        with open(os.path.join(TEMPLATE_DIR, "index.html"), 'w', encoding='utf-8') as f:
            f.write(index_html)
        
        with open(os.path.join(TEMPLATE_DIR, "hand_detail.html"), 'w', encoding='utf-8') as f:
            f.write(detail_html)

if __name__ == "__main__":
    gen = WebGenerator()
    gen.generate_all()