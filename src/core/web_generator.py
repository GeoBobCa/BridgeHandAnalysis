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
        # 1. DASHBOARD (Updated to show 4 players clearly)
        index_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Bridge Session Report</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <style>
                .player-names { font-size: 0.85em; color: #555; }
                .verdict-tag { font-weight: bold; color: #0d6efd; }
            </style>
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <h1 class="mb-4">Bridge Session Analysis</h1>
                <div class="row">
                    {% for item in hands %}
                    <div class="col-md-4 mb-4">
                        <div class="card h-100 shadow-sm border-0">
                            <div class="card-header bg-white d-flex justify-content-between align-items-center">
                                <h5 class="m-0">{{ item.facts.board }}</h5>
                                <span class="badge bg-secondary">{{ item.facts.vulnerability }}</span>
                            </div>
                            <div class="card-body">
                                <div class="mb-3 text-center">
                                    <div class="verdict-tag">{{ item.ai_analysis.verdict }}</div>
                                </div>
                                <div class="player-names mb-3 border-top border-bottom py-2 bg-light rounded px-2">
                                    <div class="d-flex justify-content-between"><span>N/S:</span> <strong>{{ item.facts.hands.North.name }} & {{ item.facts.hands.South.name }}</strong></div>
                                    <div class="d-flex justify-content-between"><span>E/W:</span> <strong>{{ item.facts.hands.East.name }} & {{ item.facts.hands.West.name }}</strong></div>
                                </div>
                                <a href="{{ item.facts.board | replace(' ', '_') }}.html" class="btn btn-primary w-100">View Analysis</a>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </body>
        </html>
        """
        
        # 2. DETAIL PAGE (Handles Red Team, Bullets, and Learning Data)
        detail_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{{ hand.facts.board }} - Analysis</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <style>
                .learning-card { border-left: 4px solid #fd7e14; background-color: #fff8f3; }
                .rec-auction-badge { font-size: 1.1em; margin-right: 5px; }
            </style>
        </head>
        <body class="bg-white">
            <div class="container py-4">
                <div class="d-flex justify-content-between mb-3">
                    <a href="index.html" class="btn btn-secondary">&larr; Dashboard</a>
                    <a href="{{ hand.handviewer_url }}" target="_blank" class="btn btn-danger">▶ Replay on BBO</a>
                </div>
                
                <div class="card mb-4 shadow-sm">
                    <div class="card-body d-flex justify-content-between align-items-center">
                        <div>
                            <h2 class="display-6 m-0">{{ hand.facts.board }}</h2>
                            <h4 class="text-primary mt-2">{{ hand.ai_analysis.verdict }}</h4>
                        </div>
                        <div class="text-end">
                            <div class="badge bg-dark mb-1">Dealer: {{ hand.facts.dealer }}</div><br>
                            <div class="badge bg-warning text-dark">Vul: {{ hand.facts.vulnerability }}</div>
                        </div>
                    </div>
                </div>

                <div class="row mb-4">
                    <div class="col-md-7">
                        <div class="card h-100">
                            <div class="card-header bg-dark text-white">The Deal</div>
                            <div class="card-body text-center">
                                <div class="row">
                                    <div class="col-12 mb-2">
                                        <small>{{ hand.facts.hands.North.name }}</small><br>
                                        <strong>North</strong><br>{{ hand.facts.hands.North.stats.distribution_str }}
                                    </div>
                                    <div class="col-4 text-start">
                                        <small>{{ hand.facts.hands.West.name }}</small><br>
                                        <strong>West</strong><br>{{ hand.facts.hands.West.stats.hcp }} HCP
                                    </div>
                                    <div class="col-4"><img src="https://bridgebase.com/mobile/images/table_felt.jpg" class="img-fluid opacity-50"></div>
                                    <div class="col-4 text-end">
                                        <small>{{ hand.facts.hands.East.name }}</small><br>
                                        <strong>East</strong><br>{{ hand.facts.hands.East.stats.hcp }} HCP
                                    </div>
                                    <div class="col-12 mt-2">
                                        <small>{{ hand.facts.hands.South.name }}</small><br>
                                        <strong>South</strong><br>{{ hand.facts.hands.South.stats.distribution_str }}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-5">
                        <div class="card h-100">
                            <div class="card-header bg-secondary text-white">Auction History</div>
                            <div class="card-body d-flex align-items-center justify-content-center">
                                <div class="alert alert-light border w-100 text-center font-monospace">
                                    {{ hand.facts.auction | join(' - ') }}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-12 mb-3">
                        <div class="card border-primary">
                            <div class="card-header bg-primary text-white">Audrey's Analysis</div>
                            <div class="card-body">
                                <ul class="list-group list-group-flush mb-3">
                                    {% for point in hand.ai_analysis.analysis_bullets %}
                                    <li class="list-group-item">🔹 {{ point }}</li>
                                    {% endfor %}
                                </ul>

                                {% if hand.ai_analysis.recommended_auction %}
                                <div class="alert alert-warning shadow-sm mt-3">
                                    <h5><span class="badge bg-warning text-dark me-2">Correction</span> Recommended Bidding Sequence:</h5>
                                    <div class="d-flex flex-wrap mt-2">
                                        {% for bid in hand.ai_analysis.recommended_auction %}
                                            <span class="badge bg-white text-dark border border-secondary rec-auction-badge p-2">{{ bid }}</span>
                                            {% if not loop.last %} <span class="text-muted align-self-center mx-1">&rarr;</span> {% endif %}
                                        {% endfor %}
                                    </div>
                                </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>

                {% if hand.ai_analysis.learning_data %}
                <h4 class="mt-4 mb-3 text-secondary">Coach's Corner</h4>
                <div class="row">
                    {% for item in hand.ai_analysis.learning_data %}
                    <div class="col-md-6 mb-3">
                        <div class="card learning-card h-100">
                            <div class="card-body">
                                <h6 class="text-uppercase text-muted small">{{ item.category }} | {{ item.player }}</h6>
                                <h5 class="card-title text-dark">{{ item.topic }}</h5>
                                <p class="card-text small text-muted">
                                    Assigned to {{ item.player }} based on this deal.
                                </p>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}

            </div>
        </body>
        </html>
        """

        with open(os.path.join(TEMPLATE_DIR, "index.html"), 'w', encoding='utf-8') as f:
            f.write(index_html)
        
        with open(os.path.join(TEMPLATE_DIR, "hand_detail.html"), 'w', encoding='utf-8') as f:
            f.write(detail_html)

if __name__ == "__main__":
    gen = WebGenerator()
    gen.generate_all()