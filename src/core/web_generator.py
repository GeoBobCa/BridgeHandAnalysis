import os
import json
import re
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
        self._create_templates()

    def generate_all(self):
        files = [f for f in os.listdir(JSON_FOLDER) if f.endswith(".json")]
        hands_data = []
        
        for f in files:
            with open(os.path.join(JSON_FOLDER, f), 'r', encoding='utf-8') as json_file:
                hands_data.append(json.load(json_file))
        
        # Sort by Board Number found in the NEW board name (e.g. "Board 13")
        def get_board_num(item):
            board_str = item['facts'].get('board', '0')
            nums = re.findall(r'\d+', board_str)
            return int(nums[0]) if nums else 0

        hands_data.sort(key=get_board_num)

        self._render("index.html", "index.html", hands=hands_data)
        
        for hand in hands_data:
            page_title = hand['facts']['board']
            safe_filename = page_title.replace(' ', '_') + ".html"
            
            hand['handviewer_url'] = "http://www.bridgebase.com/tools/handviewer.html?lin=" + \
                                     urllib.parse.quote(hand['facts']['raw_lin'])
            
            self._render("hand_detail.html", safe_filename, hand=hand, title=page_title)
            
        print(f"Website generated in: {OUTPUT_HTML_FOLDER}/")

    def _render(self, tpl, out, **kwargs):
        template = self.env.get_template(tpl)
        content = template.render(**kwargs)
        with open(os.path.join(OUTPUT_HTML_FOLDER, out), 'w', encoding='utf-8') as f:
            f.write(content)

    def _create_templates(self):
        # 1. DASHBOARD
        index_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Bridge Session Report</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        </head>
        <body class="bg-light">
            <div class="container py-5">
                <h1 class="mb-4">Bridge Session Analysis</h1>
                <div class="row">
                    {% for item in hands %}
                    <div class="col-md-3 mb-3">
                        <div class="card shadow-sm h-100">
                            <div class="card-body text-center">
                                <h5 class="card-title">{{ item.facts.board }}</h5>
                                <div class="mb-2">
                                    <span class="badge bg-secondary">Vul: {{ item.facts.vulnerability }}</span>
                                    <span class="badge bg-dark">Dlr: {{ item.facts.dealer }}</span>
                                </div>
                                <span class="badge bg-primary mb-3">{{ item.ai_analysis.verdict }}</span>
                                <a href="{{ item.facts.board | replace(' ', '_') }}.html" class="btn btn-outline-dark btn-sm w-100">View Analysis</a>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </body>
        </html>
        """
        
        # 2. DETAIL PAGE (New Card Diagram)
        detail_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{{ title }} Analysis</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <style>
                .section-header { border-bottom: 2px solid #dee2e6; margin-bottom: 1rem; padding-bottom: 0.5rem; color: #495057; }
                .bid-badge { font-family: monospace; font-size: 1.1em; padding: 8px 12px; }
                .coach-card { background-color: #f8f9fa; border-left: 5px solid #0dcaf0; }
                .adv-card { background-color: #fff3cd; border-left: 5px solid #ffc107; }
                
                /* Hand Diagram Styles */
                .hand-box { background: #fdfdfd; border: 1px solid #ccc; padding: 10px; border-radius: 5px; font-size: 0.9rem; }
                .suit-symbol { display: inline-block; width: 15px; text-align: center; font-weight: bold; }
                .suit-S { color: black; } .suit-H { color: red; }
                .suit-D { color: orange; } .suit-C { color: green; }
                .dealer-badge { background-color: #000; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; margin-left: 5px; }
            </style>
        </head>
        <body class="bg-white">
            <div class="container py-4">
                <div class="d-flex justify-content-between mb-4">
                    <a href="index.html" class="btn btn-outline-secondary">&larr; Back to Dashboard</a>
                    <h2 class="m-0">{{ title }}</h2>
                    <a href="{{ hand.handviewer_url }}" target="_blank" class="btn btn-danger">Replay Hand</a>
                </div>

                <div class="row mb-5">
                    <div class="col-md-8">
                        <div class="card bg-success bg-opacity-10 border-success">
                            <div class="card-body position-relative" style="min-height: 400px;">
                                
                                <div class="position-absolute top-50 start-50 translate-middle text-center bg-white p-3 border rounded shadow-sm" style="z-index: 2;">
                                    <strong>{{ title }}</strong><br>
                                    Dealer: {{ hand.facts.dealer }}<br>
                                    Vul: {{ hand.facts.vulnerability }}
                                </div>

                                <div class="position-absolute top-0 start-50 translate-middle-x mt-2 w-50">
                                    <div class="hand-box shadow-sm">
                                        <strong>North</strong> ({{ hand.facts.hands.North.name }})
                                        {% if hand.facts.dealer == 'North' %}<span class="dealer-badge">DLR</span>{% endif %}
                                        <div class="float-end fw-bold">{{ hand.facts.hands.North.stats.hcp }} HCP</div>
                                        <hr class="my-1">
                                        <div><span class="suit-symbol suit-S">♠</span> {{ hand.facts.hands.North.stats.cards.S }}</div>
                                        <div><span class="suit-symbol suit-H">♥</span> {{ hand.facts.hands.North.stats.cards.H }}</div>
                                        <div><span class="suit-symbol suit-D">♦</span> {{ hand.facts.hands.North.stats.cards.D }}</div>
                                        <div><span class="suit-symbol suit-C">♣</span> {{ hand.facts.hands.North.stats.cards.C }}</div>
                                    </div>
                                </div>

                                <div class="position-absolute top-50 start-0 translate-middle-y ms-2 w-25">
                                    <div class="hand-box shadow-sm">
                                        <strong>West</strong> ({{ hand.facts.hands.West.name }})
                                        {% if hand.facts.dealer == 'West' %}<span class="dealer-badge">DLR</span>{% endif %}
                                        <div class="fw-bold">{{ hand.facts.hands.West.stats.hcp }} HCP</div>
                                        <hr class="my-1">
                                        <div><span class="suit-symbol suit-S">♠</span> {{ hand.facts.hands.West.stats.cards.S }}</div>
                                        <div><span class="suit-symbol suit-H">♥</span> {{ hand.facts.hands.West.stats.cards.H }}</div>
                                        <div><span class="suit-symbol suit-D">♦</span> {{ hand.facts.hands.West.stats.cards.D }}</div>
                                        <div><span class="suit-symbol suit-C">♣</span> {{ hand.facts.hands.West.stats.cards.C }}</div>
                                    </div>
                                </div>

                                <div class="position-absolute top-50 end-0 translate-middle-y me-2 w-25">
                                    <div class="hand-box shadow-sm">
                                        <strong>East</strong> ({{ hand.facts.hands.East.name }})
                                        {% if hand.facts.dealer == 'East' %}<span class="dealer-badge">DLR</span>{% endif %}
                                        <div class="fw-bold">{{ hand.facts.hands.East.stats.hcp }} HCP</div>
                                        <hr class="my-1">
                                        <div><span class="suit-symbol suit-S">♠</span> {{ hand.facts.hands.East.stats.cards.S }}</div>
                                        <div><span class="suit-symbol suit-H">♥</span> {{ hand.facts.hands.East.stats.cards.H }}</div>
                                        <div><span class="suit-symbol suit-D">♦</span> {{ hand.facts.hands.East.stats.cards.D }}</div>
                                        <div><span class="suit-symbol suit-C">♣</span> {{ hand.facts.hands.East.stats.cards.C }}</div>
                                    </div>
                                </div>

                                <div class="position-absolute bottom-0 start-50 translate-middle-x mb-2 w-50">
                                    <div class="hand-box shadow-sm">
                                        <strong>South</strong> ({{ hand.facts.hands.South.name }})
                                        {% if hand.facts.dealer == 'South' %}<span class="dealer-badge">DLR</span>{% endif %}
                                        <div class="float-end fw-bold">{{ hand.facts.hands.South.stats.hcp }} HCP</div>
                                        <hr class="my-1">
                                        <div><span class="suit-symbol suit-S">♠</span> {{ hand.facts.hands.South.stats.cards.S }}</div>
                                        <div><span class="suit-symbol suit-H">♥</span> {{ hand.facts.hands.South.stats.cards.H }}</div>
                                        <div><span class="suit-symbol suit-D">♦</span> {{ hand.facts.hands.South.stats.cards.D }}</div>
                                        <div><span class="suit-symbol suit-C">♣</span> {{ hand.facts.hands.South.stats.cards.C }}</div>
                                    </div>
                                </div>
                                
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="card h-100">
                            <div class="card-header">Actual Auction</div>
                            <div class="card-body d-flex align-items-center justify-content-center">
                                <div class="font-monospace text-center">
                                    {{ hand.facts.auction | join(' - ') }}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <h4 class="section-header">🔍 1. Critique of Actual Play</h4>
                <div class="mb-5">
                    <ul class="list-group">
                        {% for point in hand.ai_analysis.actual_critique %}
                        <li class="list-group-item border-0">❌ {{ point }}</li>
                        {% endfor %}
                    </ul>
                </div>

                <h4 class="section-header">📘 2. The Fundamentals (Standard American)</h4>
                <div class="card mb-5 border-primary">
                    <div class="card-body">
                        <p class="lead">{{ hand.ai_analysis.basic_section.analysis }}</p>
                        {% if hand.ai_analysis.basic_section.recommended_auction %}
                        <div class="mt-3">
                            <h6>✅ Correct Standard Sequence:</h6>
                            <div class="d-flex flex-wrap gap-2">
                                {% for bid in hand.ai_analysis.basic_section.recommended_auction %}
                                <span class="badge bg-primary bid-badge">{{ bid }}</span>
                                {% endfor %}
                            </div>
                        </div>
                        {% endif %}
                    </div>
                </div>

                <h4 class="section-header">🚀 3. Advanced Concepts</h4>
                <div class="card mb-5 adv-card">
                    <div class="card-body">
                        <p>{{ hand.ai_analysis.advanced_section.analysis }}</p>
                        {% if hand.ai_analysis.advanced_section.sequence %}
                        <div class="mt-3">
                            <h6>✨ Advanced Sequence:</h6>
                            <div class="d-flex flex-wrap gap-2">
                                {% for bid in hand.ai_analysis.advanced_section.sequence %}
                                <span class="badge bg-warning text-dark bid-badge">{{ bid }}</span>
                                {% endfor %}
                            </div>
                        </div>
                        {% endif %}
                    </div>
                </div>

                <h4 class="section-header">🎓 4. Coach's Corner</h4>
                <div class="row">
                    {% for item in hand.ai_analysis.coaches_corner %}
                    <div class="col-md-6 mb-3">
                        <div class="card coach-card h-100">
                            <div class="card-body">
                                <small class="text-uppercase text-muted">{{ item.player }} | {{ item.category }}</small>
                                <h5 class="card-title">{{ item.topic }}</h5>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>

            </div>
        </body>
        </html>
        """

        with open(os.path.join(TEMPLATE_DIR, "index.html"), 'w', encoding='utf-8') as f:
            f.write(index_html)
        
        with open(os.path.join(TEMPLATE_DIR, "hand_detail.html"), 'w', encoding='utf-8') as f:
            f.write(detail_html)

if __name__ == "__main__":
    WebGenerator().generate_all()