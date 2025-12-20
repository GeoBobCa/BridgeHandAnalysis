import json
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QTableView, QVBoxLayout, 
                             QWidget, QHeaderView, QMessageBox, QFileDialog,
                             QProgressBar, QSplitter, QPushButton, QTextEdit, QLabel)
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtSql import QSqlDatabase
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, Qt
from loguru import logger

# Local Imports
from src.utils.paths import DB_PATH, INPUTS_DIR
from src.ui.hand_table_model import HandTableModel
from src.core.parsers import BridgeParser
from src.core.bridge_math import BridgeMath
from src.core.database import DatabaseManager
from src.core.handviewer import HandViewer
from src.core.ai_orchestrator import AIOrchestrator  # <--- NEW IMPORT

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Bridge Master - Hand Librarian")
        self.resize(1400, 900)
        
        # Initialize AI Orchestrator (Lazy load or init here)
        try:
            self.ai_orchestrator = AIOrchestrator()
            self.ai_enabled = True
        except Exception as e:
            logger.error(f"AI Disabled: {e}")
            self.ai_enabled = False
        
        self._connect_to_db()
        self._init_ui()
        self.backend_db = DatabaseManager(DB_PATH)

    def _connect_to_db(self):
        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName(str(DB_PATH))
        if not self.db.open():
            QMessageBox.critical(self, "Error", "Could not open database.")

    def _init_ui(self):
        # --- Menu Bar ---
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        
        import_action = QAction("&Import LIN/PBN...", self)
        import_action.triggered.connect(self.import_files_dialog)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # --- Main Layout (Splitter) ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        self.splitter = QSplitter()
        main_layout.addWidget(self.splitter)
        
        # ==========================================
        # PANEL 1: LEFT (Table + Controls)
        # ==========================================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0,0,0,0)
        
        self.table_view = QTableView()
        
        # Button Container
        btn_layout = QVBoxLayout()
        
        self.analyze_btn = QPushButton("Analyze Selected Hand with AI")
        self.analyze_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.analyze_btn.clicked.connect(self.run_ai_analysis)
        self.analyze_btn.setEnabled(self.ai_enabled)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        btn_layout.addWidget(self.analyze_btn)
        btn_layout.addWidget(self.progress_bar)
        
        left_layout.addWidget(self.table_view)
        left_layout.addLayout(btn_layout)
        
        self.splitter.addWidget(left_widget)
        
        # ==========================================
        # PANEL 2: RIGHT (Browser + AI Report)
        # ==========================================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0,0,0,0)
        
        # A. Hand Viewer (Top Half of Right Panel)
        self.browser = QWebEngineView()
        self.browser.setHtml("<h3 style='color:gray'>Select a hand to view table</h3>")
        
        # B. AI Report Area (Bottom Half of Right Panel)
        self.report_label = QLabel("AI Analysis Report:")
        self.report_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setPlaceholderText("Select a hand and click 'Analyze' to see the Teacher's feedback...")
        self.report_text.setStyleSheet("background-color: #f9f9f9; padding: 5px;")

        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.addWidget(self.browser)
        
        report_container = QWidget()
        rc_layout = QVBoxLayout(report_container)
        rc_layout.addWidget(self.report_label)
        rc_layout.addWidget(self.report_text)
        rc_layout.setContentsMargins(0,0,0,0)
        
        right_splitter.addWidget(report_container)
        right_splitter.setSizes([400, 300]) # 400px Browser, 300px Text
        
        right_layout.addWidget(right_splitter)
        
        self.splitter.addWidget(right_widget)
        self.splitter.setSizes([700, 700]) # 50/50 split
        
        # --- Setup Model ---
        self.model = HandTableModel(self.db)
        self.table_view.setModel(self.model)
        self._configure_table_view()
        
        # --- Connect Signals ---
        self.selection_model = self.table_view.selectionModel()
        self.selection_model.selectionChanged.connect(self.on_row_selected)

    def _configure_table_view(self):
        view = self.table_view
        view.setSortingEnabled(True)
        view.setAlternatingRowColors(True)
        view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        
        # Hide technical columns
        for col in ["hand_record_pbn", "hands_json", "hcp_east", "dist_points_east", 
                    "hcp_west", "dist_points_west", "dealer", "vulnerability", "handviewer_url"]:
            idx = self.model.fieldIndex(col)
            if idx >= 0:
                view.hideColumn(idx)
        
        header = view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)

    def get_selected_hand_data(self):
        """Helper to extract data from the selected row."""
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return None
        
        row_idx = indexes[0].row()
        
        # Extract basic data
        def get_val(col_name):
            return self.model.data(self.model.index(row_idx, self.model.fieldIndex(col_name)))

        hands_json = get_val("hands_json")
        if not hands_json: return None
        
        hand_data = {
            "board_id": get_val("deal_id"), # Using deal_id as proxy for board info
            "dealer": get_val("dealer"),
            "vulnerability": get_val("vulnerability"),
            "hands": json.loads(hands_json),
            # We could fetch auction from 'sessions' table here if we did a JOIN in the model,
            # but for now we send the cards.
            "auction": [] 
        }
        
        # Reconstruct Math Results
        math_results = {
            "North": {"hcp": get_val("hcp_north"), "total": get_val("dist_points_north")},
            "South": {"hcp": get_val("hcp_south"), "total": get_val("dist_points_south")},
            # We didn't bind East/West math to the model columns, but AI can re-calc or we add columns
            # For this MVP, we send N/S truth which is most critical.
        }
        
        return hand_data, math_results, get_val("handviewer_url")

    def on_row_selected(self, selected, deselected):
        """Update Browser Only."""
        data = self.get_selected_hand_data()
        if not data: return
        
        _, _, url = data
        if url:
            self.browser.setUrl(QUrl(url))
        
        # Clear previous analysis
        self.report_text.clear()
        self.report_text.setText("Click 'Analyze' to get AI feedback on this hand.")

    def run_ai_analysis(self):
        """Send data to Gemini."""
        data = self.get_selected_hand_data()
        if not data:
            QMessageBox.warning(self, "Warning", "Please select a hand first.")
            return

        hand_data, math_results, _ = data
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # Infinite spinner
        self.report_text.setText("Thinking... (Consulting Audrey Grant's rules)...")
        
        # NOTE: In a real app, use QThread here to avoid freezing UI.
        # For MVP, we run blocking call.
        try:
            result = self.ai_orchestrator.analyze_hand(hand_data, math_results)
            
            if "error" in result:
                self.report_text.setText(f"Error: {result['error']}")
            else:
                # Format the JSON into HTML for the text box
                html_report = f"""
                <h2>Bridge Master Analysis</h2>
                <hr>
                <h3><b>Bidding Critique:</b></h3>
                <p>{result.get('bidding_critique', 'N/A')}</p>
                
                <h3><b>Play Analysis:</b></h3>
                <p>{result.get('play_analysis', 'N/A')}</p>
                
                <h3 style='color:blue'><b>Study Recommendation:</b></h3>
                <p><i>{result.get('study_recommendation', 'N/A')}</i></p>
                
                <hr>
                <small>Verdict: {result.get('verdict', 'N/A')}</small>
                """
                self.report_text.setHtml(html_report)
                
        except Exception as e:
            self.report_text.setText(f"Crash: {str(e)}")
        
        finally:
            self.progress_bar.setVisible(False)

    def import_files_dialog(self):
        start_dir = str(INPUTS_DIR) if INPUTS_DIR.exists() else str(Path.home())
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Bridge Files", start_dir, "Bridge Files (*.lin *.pbn);;All Files (*)"
        )
        if file_paths:
            self.run_import_process(file_paths)

    def run_import_process(self, file_paths):
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(file_paths))
        self.progress_bar.setValue(0)
        
        count = 0
        self.backend_db.connect()
        try:
            for f_path in file_paths:
                path_obj = Path(f_path)
                deals = BridgeParser.parse_file(path_obj)
                for hand_data in deals:
                    math_results = {}
                    for direction, cards in hand_data['hands'].items():
                        math_results[direction] = BridgeMath.evaluate_hand(cards)
                    
                    # Generate URL
                    hv_url = HandViewer.generate_url(hand_data)
                    
                    self.backend_db.save_deal(hand_data, math_results, hv_url)
                count += 1
                self.progress_bar.setValue(count)
            QMessageBox.information(self, "Success", f"Processed {count} files.")
        except Exception as e:
            logger.error(f"Import failed: {e}")
            QMessageBox.critical(self, "Import Error", str(e))
        finally:
            self.backend_db.close()
            self.progress_bar.setVisible(False)
            self.model.select()

    def closeEvent(self, event):
        if self.db.isOpen():
            self.db.close()
        event.accept()