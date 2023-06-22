from logger_tt import logger
import json
import os
import subprocess
import sys

from PySide6.QtCore import Qt, QFile, QIODevice, Signal, Slot
from PySide6.QtGui import QContextMenuEvent, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMenu,
    QMessageBox,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
    QInputDialog,
)


class GitUpdater(QWidget):
    """
    This class controls the layout and functionality for the GitUpdater panel,
    Subclasses QWidget to allow emitting signals.
    """

    # Signal emitter for this class
    gitupdater_signal = Signal(str)

    def __init__(self):
        logger.info("Starting GitUpdater initialization")
        super().__init__()

        self.setWindowTitle("GitUpdater")
        self.resize(400, 300)

        self.setup_ui()

        self.locations = []
        self.load_locations()

    def setup_ui(self):
        self.central_widget = QWidget(self)
        self.layout = QVBoxLayout(self.central_widget)

        self.tree_view = QTreeView(self.central_widget)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)

        self.model = QStandardItemModel(self.tree_view)
        self.tree_view.setModel(self.model)

        self.layout.addWidget(self.tree_view)

        self.add_mods_button = QPushButton("Add Mods Folder")
        self.add_mods_button.clicked.connect(self.add_mods_folder)
        self.layout.addWidget(self.add_mods_button)

        self.add_github_button = QPushButton("Add GitHub Link")
        self.add_github_button.clicked.connect(self.add_github_link)
        self.layout.addWidget(self.add_github_button)

        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.update_folders)
        self.layout.addWidget(self.update_button)

        self.setLayout(self.layout)

    def load_locations(self):
        try:
            with open("locations.json", "r") as file:
                self.locations = json.load(file)
                self.update_tree_view()
        except FileNotFoundError:
            pass

    def save_locations(self):
        with open("locations.json", "w") as file:
            json.dump(self.locations, file)

    def update_tree_view(self):
        self.model.clear()

        for location in self.locations:
            item = QStandardItem(location)
            self.model.appendRow(item)

    def show_context_menu(self, position):
        index = self.tree_view.indexAt(position)
        if index.isValid():
            menu = QMenu(self)
            edit_action = menu.addAction("Edit")
            delete_action = menu.addAction("Delete")

            action = menu.exec_(self.tree_view.viewport().mapToGlobal(position))

            if action == edit_action:
                self.edit_location(index.row())
            elif action == delete_action:
                self.delete_location(index.row())

    def edit_location(self, row):
        location = self.locations[row]
        new_location, ok = QInputDialog.getText(
            self, "Edit Location", "Enter the new location:", text=location
        )
        if ok:
            self.locations[row] = new_location
            self.update_tree_view()
            self.save_locations()

    def delete_location(self, row):
        reply = QMessageBox.question(
            self,
            "Delete Location",
            "Are you sure you want to delete this location?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            del self.locations[row]
            self.update_tree_view()
            self.save_locations()

    @Slot()
    def add_mods_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Mods Folder", options=QFileDialog.ShowDirsOnly
        )
        if folder:
            git_folders = []
            for root, dirs, files in os.walk(folder):
                if ".git" in dirs:
                    git_folders.append(root)

            if git_folders:
                self.locations.extend(git_folders)
                self.update_tree_view()
                self.save_locations()

    @Slot()
    def add_github_link(self):
        link, ok = QInputDialog.getText(
            self, "Add GitHub Link", "Enter the GitHub link:"
        )
        if ok:
            process = subprocess.Popen(
                ["git", "clone", link],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            _, error = process.communicate()

            if process.returncode == 0:
                folder = link.split("/")[-1].split(".")[0]
                self.locations.append(folder)
                self.update_tree_view()
                self.save_locations()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to clone the repository:\n{error}",
                    QMessageBox.Ok,
                )

    @Slot()
    def update_folders(self):
        for location in self.locations:
            os.chdir(location)
            process = subprocess.Popen(
                ["git", "pull", "--rebase"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            _, error = process.communicate()

            if process.returncode != 0:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to update the folder '{location}':\n{error}",
                    QMessageBox.Ok,
                )
                break
        else:
            QMessageBox.information(
                self, "Update", "All folders have been updated.", QMessageBox.Ok
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    git_updater = GitUpdater()
    git_updater.show()
    sys.exit(app.exec())
