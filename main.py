from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMessageBox
import MySQLdb as mdb
import sys
from new_window import Ui_MainWindow


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        try:
            self.conn = mdb.connect(
                host='intizar1.beget.tech',
                user='intizar1_ndfl',
                passwd='iisaeva-22',
                db='intizar1_ndfl',

            )
            print("Успешное подключение к базе данных!")
            self.setup_ui()

        except mdb.Error as e:
            QMessageBox.critical(self, "Ошибка подключения",
                                 f"Не удалось подключиться к базе данных:\n{e}")
            sys.exit(1)

    def setup_ui(self):
        self.setWindowTitle("Калькулятор страховых взносов")
        self.load_positions()
        self.create_insurance_checks()
        self.radioButton.setText(self.get_types_operation()[0][0])
        self.radioButton_2.setText(self.get_types_operation()[1][0])

        self.pushButton.clicked.connect(self.calculate)
        self.pushButton_2.clicked.connect(self.save_to_db)

    def load_positions(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, post_name, salary FROM Posts")

            self.comboBox.clear()
            for pos in cursor.fetchall():
                self.comboBox.addItem(f"{pos[1]} ({pos[2]} руб.)", userData=pos[0])

        except mdb.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить должности: {e}")

    def create_insurance_checks(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, contrib_name FROM Insurance_Contributions_Types")
            buttons = QtWidgets.QButtonGroup(self)
            buttons.setExclusive(False)
            layout = QtWidgets.QVBoxLayout()
            for contrib in cursor.fetchall():
                cb = QtWidgets.QCheckBox(contrib[1])
                buttons.addButton(cb, contrib[0])
                cb.setChecked(True)
                cb.setProperty("contribution_id", contrib[0])
                layout.addWidget(cb)

            if self.groupBox_2.layout():
                QtWidgets.QWidget().setLayout(self.groupBox_2.layout())
            self.groupBox_2.setLayout(layout)

        except mdb.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить взносы: {e}")

    def get_types_operation(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT oper_name FROM Operations_type;")
        operations = cursor.fetchall()
        return list(operations)

    def calculate(self):
        try:
            position_id = self.comboBox.currentData()
            operation_type = self.radioButtons.checkedId()

            cursor = self.conn.cursor()
            cursor.callproc('CalculateSalaryAndContribution', (position_id, 0, 0))
            cursor.execute("SELECT @_CalculateSalaryAndContribution_1, @_CalculateSalaryAndContribution_2")
            salary_pay, insurance_sum = cursor.fetchone()

            result = salary_pay if operation_type == 1 else insurance_sum
            QMessageBox.information(self, "Результат", f"Сумма: {result:.2f} руб.")

        except mdb.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка расчета: {e}")

    def save_to_db(self):
        try:
            position_id = self.comboBox.currentData()
            operation_type = 1 if self.radioButton_2.isChecked() else 2

            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO Accrual (accrual_date, summa, id_oper, id_post)
                VALUES (CURDATE(), 
                (SELECT salary FROM Posts WHERE id = %s), 
                1, %s)
            """, (position_id, position_id))

            accrual_id = cursor.lastrowid
            cursor.callproc('ProcessAccrualWithLogging', (accrual_id, operation_type, 0))
            self.conn.commit()

            QMessageBox.information(self, "Успех", "Данные успешно сохранены!")

        except mdb.Error as e:
            self.conn.rollback()
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {e}")

    def closeEvent(self, event):
        if hasattr(self, 'conn'):
            self.conn.close()
        event.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())