import sys
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QStatusBar, QMessageBox, QFileDialog, QHeaderView,
    QCheckBox, QDoubleSpinBox, QGroupBox, QDialog, QAbstractItemView, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from typing import List
from models.bond import Bond
from data.moex_api import MoexAPI
from data.bond_calculator import BondCalculator
from data.trading_hours import get_current_trading_status, is_trading_now
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class FetchBondsWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def run(self):
        try:
            api = MoexAPI()
            bonds = api.get_all_bonds()
            self.finished.emit(bonds)
        except Exception as e:
            self.error.emit(str(e))


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=3, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)


class ComparisonDialog(QDialog):
    def __init__(self, bond1: Bond, bond2: Bond, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сравнение облигаций")
        self.resize(800, 400)

        layout = QVBoxLayout(self)

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Параметр", bond1.secid, bond2.secid])
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        params = [
            ("Название", bond1.name, bond2.name),
            ("ISIN", bond1.isin, bond2.isin),
            ("Сектор", bond1.sector, bond2.sector),
            ("Купон, %", f"{bond1.coupon_rate:.2f}", f"{bond2.coupon_rate:.2f}"),
            ("Период купона, дни", str(bond1.coupon_period), str(bond2.coupon_period)),
            ("Дата след. купона", bond1.coupon_next_date.isoformat(), bond2.coupon_next_date.isoformat()),
            ("Цена, %", f"{bond1.price:.2f}", f"{bond2.price:.2f}"),
            ("НКД", f"{bond1.accrued_interest:.2f}", f"{bond2.accrued_interest:.2f}"),
            ("YTM, %", f"{bond1.yield_to_maturity or 0:.2f}", f"{bond2.yield_to_maturity or 0:.2f}"),
            ("Текущая доходность, %", f"{bond1.current_yield:.2f}", f"{bond2.current_yield:.2f}"),
            ("Дата погашения", bond1.maturity_date.isoformat(), bond2.maturity_date.isoformat()),
            ("Лет до погашения", f"{bond1.years_to_maturity:.2f}", f"{bond2.years_to_maturity:.2f}"),
            ("Номинал, руб", str(bond1.face_value), str(bond2.face_value)),
        ]

        table.setRowCount(len(params))
        for row, (param, val1, val2) in enumerate(params):
            table.setItem(row, 0, QTableWidgetItem(param))
            table.setItem(row, 1, QTableWidgetItem(val1))
            table.setItem(row, 2, QTableWidgetItem(val2))

        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.resizeRowsToContents()
        layout.addWidget(table)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Анализатор Облигаций (MOEX)")
        self.resize(1200, 900)

        self.bonds: List[Bond] = []
        self.best_bond: Bond = None
        self.calculator_params = {
            "min_years": 0.5,
            "max_years": 10.0,
            "prefer_gov": True,
            "min_ytm": 1.0
        }
        self.auto_update_enabled = False

        self.init_ui()

        self.trading_status_timer = QTimer(self)
        self.trading_status_timer.timeout.connect(self.update_trading_status)
        self.trading_status_timer.start(60_000)
        self.update_trading_status()

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.auto_update_if_trading)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        top_layout = QHBoxLayout()

        btn_layout = QVBoxLayout()
        self.btn_fetch = QPushButton("Загрузить облигации с MOEX")
        self.btn_save = QPushButton("Сохранить в Excel")
        self.btn_compare = QPushButton("Сравнить выбранные")
        self.btn_schedule = QPushButton("Расписание торгов")
        self.btn_auto_update = QPushButton("Автообновление: ВЫКЛ")
        self.btn_auto_update.setCheckable(True)

        self.btn_compare.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.btn_fetch.clicked.connect(self.fetch_bonds)
        self.btn_save.clicked.connect(self.save_to_excel)
        self.btn_compare.clicked.connect(self.compare_selected)
        self.btn_schedule.clicked.connect(self.show_trading_schedule)
        self.btn_auto_update.clicked.connect(self.toggle_auto_update)

        btn_layout.addWidget(self.btn_fetch)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_compare)
        btn_layout.addWidget(self.btn_schedule)
        btn_layout.addWidget(self.btn_auto_update)
        btn_layout.addStretch()
        top_layout.addLayout(btn_layout)

        filter_group = QGroupBox("Фильтры анализа")
        filter_layout = QFormLayout()

        self.min_years_spin = QDoubleSpinBox()
        self.min_years_spin.setRange(0.1, 30.0)
        self.min_years_spin.setSingleStep(0.1)
        self.min_years_spin.setValue(self.calculator_params["min_years"])
        filter_layout.addRow("Мин. срок до погашения (лет):", self.min_years_spin)

        self.max_years_spin = QDoubleSpinBox()
        self.max_years_spin.setRange(0.5, 30.0)
        self.max_years_spin.setSingleStep(0.5)
        self.max_years_spin.setValue(self.calculator_params["max_years"])
        filter_layout.addRow("Макс. срок до погашения (лет):", self.max_years_spin)

        self.prefer_gov_check = QCheckBox("Предпочитать гособлигации")
        self.prefer_gov_check.setChecked(self.calculator_params["prefer_gov"])
        filter_layout.addRow("", self.prefer_gov_check)

        self.min_ytm_spin = QDoubleSpinBox()
        self.min_ytm_spin.setRange(0.0, 50.0)
        self.min_ytm_spin.setSingleStep(0.1)
        self.min_ytm_spin.setValue(self.calculator_params["min_ytm"])
        filter_layout.addRow("Мин. YTM (%):", self.min_ytm_spin)

        self.btn_apply_filters = QPushButton("Применить фильтры и пересчитать")
        self.btn_apply_filters.setEnabled(False)
        self.btn_apply_filters.clicked.connect(self.apply_filters)
        filter_layout.addRow("", self.btn_apply_filters)

        filter_group.setLayout(filter_layout)
        top_layout.addWidget(filter_group)
        main_layout.addLayout(top_layout)

        self.best_label = QLabel("Лучшая облигация: не определена")
        self.best_label.setStyleSheet("font-weight: bold; color: green; font-size: 14px;")
        main_layout.addWidget(self.best_label)

        self.table = QTableWidget()
        self.setup_table()
        self.table.setSelectionMode(QAbstractItemView.MultiSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        main_layout.addWidget(self.table)

        self.canvas = MplCanvas(self, width=5, height=3, dpi=100)
        main_layout.addWidget(self.canvas)

        # Простой индикатор загрузки (без процентов)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # неопределённый прогресс
        main_layout.addWidget(self.progress_bar)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готово")

    def setup_table(self):
        headers = [
            "SECID", "ISIN", "Название", "Купон, %", "Цена, %",
            "YTM, %", "Тек. дох-ть, %", "Погашение", "Лет до погаш.", "Сектор"
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    def on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        self.btn_compare.setEnabled(len(selected_rows) == 2)

    def fetch_bonds(self):
        self.btn_fetch.setEnabled(False)
        self.btn_auto_update.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_bar.showMessage("Загрузка ВСЕХ облигаций с MOEX...")

        self.worker = FetchBondsWorker()
        self.worker.finished.connect(self.on_bonds_loaded)
        self.worker.error.connect(self.on_fetch_error)
        self.worker.start()

    def on_bonds_loaded(self, bonds: List[Bond]):
        self.bonds = bonds
        self.btn_fetch.setEnabled(True)
        self.btn_save.setEnabled(len(bonds) > 0)
        self.btn_apply_filters.setEnabled(len(bonds) > 0)
        self.btn_auto_update.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(f"Загружено {len(bonds)} облигаций")
        self.apply_filters()
        self.update_trading_status()

    def on_fetch_error(self, error_msg: str):
        self.btn_fetch.setEnabled(True)
        self.btn_auto_update.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Ошибка загрузки")
        QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные:\n{error_msg}")

    def apply_filters(self):
        if not self.bonds:
            return

        self.calculator_params.update({
            "min_years": self.min_years_spin.value(),
            "max_years": self.max_years_spin.value(),
            "prefer_gov": self.prefer_gov_check.isChecked(),
            "min_ytm": self.min_ytm_spin.value()
        })

        calculator = BondCalculator(
            min_years_to_maturity=self.calculator_params["min_years"],
            max_years_to_maturity=self.calculator_params["max_years"],
            prefer_government=self.calculator_params["prefer_gov"],
            min_ytm_threshold=self.calculator_params["min_ytm"]
        )

        self.best_bond = calculator.find_best_bond(self.bonds)
        top_bonds = calculator.get_top_bonds(self.bonds, top_n=20)

        self.update_best_bond_display()
        self.update_table(top_bonds)
        self.update_chart()
        self.status_bar.showMessage("Фильтры применены")

    def update_best_bond_display(self):
        if self.best_bond:
            text = (
                f"Лучшая облигация: {self.best_bond.secid} "
                f"(YTM: {self.best_bond.yield_to_maturity:.2f}%, "
                f"Цена: {self.best_bond.price:.2f}%)"
            )
            self.best_label.setText(text)
        else:
            self.best_label.setText("Лучшая облигация: не найдена")

    def update_table(self, bonds: List[Bond]):
        self.table.setRowCount(len(bonds))
        for row, bond in enumerate(bonds):
            self.table.setItem(row, 0, QTableWidgetItem(bond.secid))
            self.table.setItem(row, 1, QTableWidgetItem(bond.isin or ""))
            self.table.setItem(row, 2, QTableWidgetItem(bond.name[:60]))
            self.table.setItem(row, 3, QTableWidgetItem(f"{bond.coupon_rate:.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{bond.price:.2f}"))
            ytm = f"{bond.yield_to_maturity:.2f}" if bond.yield_to_maturity else "—"
            self.table.setItem(row, 5, QTableWidgetItem(ytm))
            self.table.setItem(row, 6, QTableWidgetItem(f"{bond.current_yield:.2f}"))
            self.table.setItem(row, 7, QTableWidgetItem(bond.maturity_date.isoformat()))
            self.table.setItem(row, 8, QTableWidgetItem(f"{bond.years_to_maturity:.2f}"))
            self.table.setItem(row, 9, QTableWidgetItem(bond.sector))
        self.table.resizeRowsToContents()

    def update_chart(self):
        if not self.bonds:
            self.canvas.axes.clear()
            self.canvas.draw()
            return

        filtered_bonds = []
        for bond in self.bonds:
            ytm_val = bond.yield_to_maturity
            if ytm_val is None or ytm_val < self.calculator_params["min_ytm"]:
                continue
            ytm = bond.years_to_maturity
            if not (self.calculator_params["min_years"] <= ytm <= self.calculator_params["max_years"]):
                continue
            if bond.price <= 0 or bond.price > 200:
                continue
            filtered_bonds.append(bond)

        ytm_values = [b.yield_to_maturity for b in filtered_bonds if b.yield_to_maturity is not None]

        self.canvas.axes.clear()
        if ytm_values:
            self.canvas.axes.hist(ytm_values, bins=20, color='skyblue', edgecolor='black', alpha=0.7)
            self.canvas.axes.set_title('Распределение доходности к погашению (YTM)')
            self.canvas.axes.set_xlabel('YTM (%)')
            self.canvas.axes.set_ylabel('Количество облигаций')
            self.canvas.axes.grid(True, linestyle='--', alpha=0.5)
        else:
            self.canvas.axes.text(0.5, 0.5, 'Нет данных для графика',
                                  horizontalalignment='center',
                                  verticalalignment='center',
                                  transform=self.canvas.axes.transAxes,
                                  fontsize=12, color='gray')
        self.canvas.draw()

    def compare_selected(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if len(selected_rows) != 2:
            return

        row1 = selected_rows[0].row()
        row2 = selected_rows[1].row()
        secid1 = self.table.item(row1, 0).text()
        secid2 = self.table.item(row2, 0).text()

        bond1 = next((b for b in self.bonds if b.secid == secid1), None)
        bond2 = next((b for b in self.bonds if b.secid == secid2), None)

        if bond1 and bond2:
            dialog = ComparisonDialog(bond1, bond2, self)
            dialog.exec_()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось найти данные для выбранных облигаций.")

    def save_to_excel(self):
        if not self.bonds:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для сохранения.")
            return

        default_name = f"bond_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить анализ облигаций", default_name, "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            all_data = [bond.to_dict() for bond in self.bonds]
            df_all = pd.DataFrame(all_data)
            df_all["YTM, %"] = pd.to_numeric(df_all["YTM, %"], errors='coerce')
            df_all = df_all.sort_values(by="YTM, %", ascending=False)

            best_dict = self.best_bond.to_dict() if self.best_bond else {}
            df_best = pd.DataFrame([best_dict]) if best_dict else pd.DataFrame()

            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                if not df_best.empty:
                    df_best.to_excel(writer, sheet_name="Лучшая облигация", index=False)
                df_all.to_excel(writer, sheet_name="Все облигации", index=False)

            self.status_bar.showMessage(f"Данные сохранены: {file_path}")
            QMessageBox.information(self, "Успех", f"Анализ сохранён в:\n{file_path}")

        except Exception as e:
            error_msg = f"Ошибка при сохранении файла:\n{str(e)}"
            self.status_bar.showMessage("Ошибка сохранения")
            QMessageBox.critical(self, "Ошибка", error_msg)

    def show_trading_schedule(self):
        from gui.trading_schedule_dialog import TradingScheduleDialog
        dialog = TradingScheduleDialog(self)
        dialog.exec_()

    def toggle_auto_update(self):
        self.auto_update_enabled = self.btn_auto_update.isChecked()
        if self.auto_update_enabled:
            self.btn_auto_update.setText("Автообновление: ВКЛ")
            self.update_timer.start(30_000)
            self.status_bar.showMessage("Автообновление включено")
        else:
            self.btn_auto_update.setText("Автообновление: ВЫКЛ")
            self.update_timer.stop()
            self.status_bar.showMessage("Автообновление выключено")

    def auto_update_if_trading(self):
        if not self.auto_update_enabled or not self.bonds or not is_trading_now():
            return
        self.status_bar.showMessage("Автообновление: загрузка новых котировок...")
        self.fetch_bonds()

    def update_trading_status(self):
        status = get_current_trading_status()
        user_msg = self.status_bar.currentMessage()
        if "Автообновление" not in user_msg and "Загрузка" not in user_msg:
            self.status_bar.showMessage(f"{status} | {user_msg}")