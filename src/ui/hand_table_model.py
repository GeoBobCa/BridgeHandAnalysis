from PyQt6.QtSql import QSqlTableModel
from PyQt6.QtCore import Qt

class HandTableModel(QSqlTableModel):
    """
    Adapter between the SQLite 'deals' table and the GUI TableView.
    Handles column renaming and hiding raw technical data.
    """
    def __init__(self, db_connection):
        super().__init__(db=db_connection)
        
        self.setTable("deals")
        self.setEditStrategy(QSqlTableModel.EditStrategy.OnFieldChange)
        self.select() # Load data
        
        self._setup_headers()

    def _setup_headers(self):
        """Define which columns are visible and their human names."""
        # Map DB column names to Display names
        headers = {
            "deal_id": "Deal ID",
            "dealer": "Dealer",
            "vulnerability": "Vul",
            "hcp_north": "N HCP",
            "dist_points_north": "N Total",
            "hcp_south": "S HCP",
            "dist_points_south": "S Total"
        }

        # Apply Headers
        for i in range(self.columnCount()):
            col_name = self.record().fieldName(i)
            if col_name in headers:
                self.setHeaderData(i, Qt.Orientation.Horizontal, headers[col_name])
            else:
                # Hide technical/ugly columns (JSON, raw PBN)
                # We hide them from the view, but the data is still there if needed.
                # Note: We do this in the View usually, but setting headers here helps.
                pass

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """
        Override data() if you want to customize how cells appear 
        (e.g., centering text, coloring high HCP hands).
        """
        if role == Qt.ItemDataRole.TextAlignmentRole:
            # Center align everything for neatness
            return Qt.AlignmentFlag.AlignCenter

        return super().data(index, role)