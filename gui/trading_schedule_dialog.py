from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView
)
from PyQt5.QtCore import Qt


class TradingScheduleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Расписание торгов (Московская биржа)")
        self.resize(600, 300)

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "<b>Время указано по Московскому часовому поясу (МСК = UTC+3)</b><br>"
            "Актуально для рублёвых облигаций (рынок Бонды, режим T+ и T0)."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Режим", "Время (МСК)", "Описание"])
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)

        schedule_data = [
            ("Основная сессия (T+)", "10:00 – 18:40", "Основные торги по облигациям. Расчёт через T+ (обычно T+2)."),
            ("Дополнительная сессия (T0)", "19:00 – 23:50", "Торги без риска изменения цены (T0). Доступны не все облигации."),
            ("Преклот", "09:50 – 10:00", "Подача заявок до открытия основной сессии."),
            ("Посткло", "18:40 – 19:00", "Подача заявок после основной сессии (для T0)."),
            ("Ночная сессия", "—", "Для облигаций не проводится (только для валюты и драгметаллов).")
        ]

        table.setRowCount(len(schedule_data))
        for row, (mode, time, desc) in enumerate(schedule_data):
            table.setItem(row, 0, QTableWidgetItem(mode))
            table.setItem(row, 1, QTableWidgetItem(time))
            table.setItem(row, 2, QTableWidgetItem(desc))

        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.resizeRowsToContents()
        layout.addWidget(table)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)