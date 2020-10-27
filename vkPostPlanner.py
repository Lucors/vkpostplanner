# -*- coding: utf-8 -*-
#SYSTEM
import os
import sys
import json
import time
import datetime
from threading import Thread
#WEB
import vk_api
from vk_api.utils import get_random_id
from vk_api.longpoll import VkLongPoll, VkEventType
from requests.exceptions import HTTPError
#GUI
from PySide2.QtWidgets import QApplication, QMainWindow, QWidget,  QTabWidget
from PySide2.QtWidgets import QGridLayout, QLabel, QPushButton, QDialog, QFrame
from PySide2.QtWidgets import QComboBox, QDateEdit, QLineEdit, QFileDialog
from PySide2.QtCore import Qt, QDate, QObject, Signal, Slot
from PySide2.QtGui import QIcon


#Глобальные переменные
vkConnector = None


class ConsoleIO:
	@staticmethod
	def error(msg):
		ConsoleIO().log(msg, prefix="<!>")

	@staticmethod
	def warn(msg):
		ConsoleIO().log(msg, prefix="<?>")
		
	@staticmethod
	def log(msg, prefix="<->"):
		output = datetime.datetime.today().strftime("%m.%d %H:%M:%S")
		output += ' ' + prefix + ' ' + msg
		print(output)


class VkConnector():
	def __init__(self, connectionToken):
		global vkConnector
		vkConnector = self
		self.connect(connectionToken)

	def connect(self, connectionToken):
		try:
			self.vkSession = vk_api.VkApi(token = connectionToken)
			self.vk = self.vkSession.get_api()
			self.vkUpload = vk_api.VkUpload(self.vk)
		except Exception as ex:
			ConsoleIO().error("Ошибка подключение к VK: "  + str(ex))
			sys.exit(1)


class AutoPlanner(QWidget, QObject):

	groupChanged = Signal(str)
	autoPlanningEnded = Signal()

	def __init__(self, profileData):
		super().__init__()
		self.profileData = profileData
		self.__initGUI__()
		self.__initLogic__()

	def __del__(self):
		ConsoleIO().warn("Уничтожен Планировщик")

	def __initGUI__(self):
		self.mainLayout = QGridLayout(self)

		groupSelectorLbl = QLabel("Группа:")
		self.mainLayout.addWidget(groupSelectorLbl, 0, 0)
		self.groupSelector = QComboBox()
		for group in self.profileData["groupsData"]:
			self.groupSelector.addItem(group["groupName"])
		self.mainLayout.addWidget(self.groupSelector, 1, 0)

		lGroupIDLbl = QLabel("ID Группы:")
		self.mainLayout.addWidget(lGroupIDLbl, 0, 1)
		self.lGroupID = QLineEdit("Неопр.")
		self.lGroupID.setReadOnly(True)
		self.mainLayout.addWidget(self.lGroupID, 1, 1)

		lAlbumIDLbl = QLabel("ID Альбома:")
		self.mainLayout.addWidget(lAlbumIDLbl, 0, 2)
		self.lAlbumID = QLineEdit("Неопр.")
		self.lAlbumID.setReadOnly(True)
		self.mainLayout.addWidget(self.lAlbumID, 1, 2)

		publishDateLbl = QLabel("Дата публикации:")
		self.mainLayout.addWidget(publishDateLbl, 2, 0)
		self.publishDateField = QDateEdit(QDate.currentDate())
		self.publishDateField.setMinimumDate(QDate.currentDate())
		self.publishDateField.setCalendarPopup(True)
		self.mainLayout.addWidget(self.publishDateField, 2, 1, 1, 2)

		hourSelectorLbl = QLabel("Время начала:")
		self.mainLayout.addWidget(hourSelectorLbl, 3, 0)
		self.hourSelector = QComboBox()
		hourStart = datetime.datetime.now().hour+1
		if (hourStart > 23 or hourStart < 8):
			hourStart = 8
		for hour in range(hourStart, 23):
			self.hourSelector.addItem(str(hour))
		self.mainLayout.addWidget(self.hourSelector, 4, 0)

		periodSelectorLbl = QLabel("Период планировщика:")
		self.mainLayout.addWidget(periodSelectorLbl, 3, 1)
		self.periodSelector = QComboBox()
		for period in range(1, 4):
			self.periodSelector.addItem("Раз в " + str(period) + "ч.")
		self.mainLayout.addWidget(self.periodSelector, 4, 1, 1, 2)

		filePathLbl = QLabel("Путь к файлам:")
		self.mainLayout.addWidget(filePathLbl, 5, 0)
		self.filesPathLine = QLineEdit()
		self.mainLayout.addWidget(self.filesPathLine, 6, 0, 1, 2)
		self.filePathSelector = QPushButton("...") 
		self.mainLayout.addWidget(self.filePathSelector, 6, 2)

		hLine = QFrame()
		hLine.setFrameShape(QFrame.HLine)
		hLine.setFrameShadow(QFrame.Sunken)
		self.mainLayout.addWidget(hLine, 7, 0, 1, 3)

		self.locked = False
		self.lockButton = QPushButton("Заблокировать")
		self.mainLayout.addWidget(self.lockButton, 8, 0)
		self.startButton = QPushButton("Начать")
		self.startButton.setEnabled(False)
		self.mainLayout.addWidget(self.startButton, 8, 2)

	def __initLogic__(self):
		self.filePathSelector.clicked.connect(self.__defPath)
		self.lockButton.clicked.connect(self.__toogleLock)
		self.groupSelector.highlighted.connect(self.settingGroupData)
		self.startButton.clicked.connect(self.__startAutoPlanning)
		self.autoPlanningEnded.connect(self.__endAutoPlanning)

	def __defPath(self):
		filesPath = QFileDialog.getExistingDirectory(self, "Выберите папку с файлами", "", 
                                       QFileDialog.ShowDirsOnly)
		self.filesPathLine.setText(filesPath)

	def settingGroupData(self, index):
		self.lGroupID.setText(str(self.profileData["groupsData"][index]["groupID"]))
		self.lAlbumID.setText(str(self.profileData["groupsData"][index]["albumID"]))
		self.groupChanged.emit(self.profileData["groupsData"][index]["groupName"])

	def __toogleLock(self):
		if (self.locked):
			self.lockButton.setText("Заблокировать")
			self.groupSelector.setEnabled(True)
			self.lGroupID.setEnabled(True)
			self.lAlbumID.setEnabled(True)
			self.publishDateField.setEnabled(True)
			self.hourSelector.setEnabled(True)
			self.periodSelector.setEnabled(True)
			self.periodSelector.setEnabled(True)
			self.filesPathLine.setEnabled(True)
			self.filePathSelector.setEnabled(True)
			self.startButton.setEnabled(False)
			self.locked = False
		else:
			self.lockButton.setText("Разблокировать")
			self.groupSelector.setEnabled(False)
			self.lGroupID.setEnabled(False)
			self.lAlbumID.setEnabled(False)
			self.publishDateField.setEnabled(False)
			self.hourSelector.setEnabled(False)
			self.periodSelector.setEnabled(False)
			self.periodSelector.setEnabled(False)
			self.filesPathLine.setEnabled(False)
			self.filePathSelector.setEnabled(False)
			self.startButton.setEnabled(True)
			self.locked = True

	def __startAutoPlanning(self):
		self.startButton.setEnabled(False)
		self.lockButton.setEnabled(False)
		thhredAutoPlanning = Thread(target=self.__AutoPlanningBody)
		thhredAutoPlanning.start()
		
	def __AutoPlanningBody(self):
		global vkConnector	
		try:
#Код Андрея (измененный)
			publishHour = int(self.hourSelector.currentText())
			publishPeriod = self.periodSelector.currentIndex()+1
			path = self.filesPathLine.text()
			if (path[-1] == '\\' or path[-1] != '/'):
				path += '/'
			ConsoleIO().log("Каталог: " + path)
			files = os.listdir(path)
			for filename in files:
				if filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg'):
					ConsoleIO().log("Текущий файл: " + filename)
					photoPath = path + filename
					albumID = self.lAlbumID.text()
					groupID = self.lGroupID.text()
					photoID = (vkConnector.vkUpload.photo(photos = photoPath, album_id = albumID, group_id = groupID))[0]["id"]
					
					preUnixDate = self.publishDateField.date().toString(Qt.ISODate) + ' ' + str(publishHour) + ':00:00'
					unixDate = int(time.mktime(time.strptime(preUnixDate, '%Y-%m-%d %H:%M:%S')))
					postAttachment = "photo-" + groupID + "_" + str(photoID)
					
					postMessage = ""
					potentialMessageFile = filename[0:filename.rfind(".")] + ".desc"
					if (potentialMessageFile in files):
						ConsoleIO().log("Обнаружен файл описания поста: " + potentialMessageFile)
						messageFile = open(path + potentialMessageFile, 'r', encoding = "utf-8")
						postMessage = messageFile.read()
						messageFile.close()
						
					vkConnector.vk.wall.post(publish_date = unixDate, owner_id = ('-' + groupID), 
											from_group = 1, attachments = postAttachment, message = postMessage)

					if publishHour < 22:
						publishHour = publishHour + publishPeriod
					elif publishHour >= 22:
						self.publishDateField.setDate(self.publishDateField.date().addDays(1))
						publishHour = 8
		except Exception as ex:
			ConsoleIO().error("Ошибка автопланировщика: "  + str(ex))
		finally:
			ConsoleIO().log("Планировщик окончил работу")
			self.autoPlanningEnded.emit() 

	def __endAutoPlanning(self):
		self.lockButton.setEnabled(True)
		self.__toogleLock()


class TokenEditor(QDialog, QObject):
	
	def __init__(self, profileData):
		super().__init__()
		self.profileData = profileData
		self.__initGUI__()
		self.__initLogic__()
		
	def __initGUI__(self):
		self.setWindowTitle("Редактор токена")
		self.setWindowIcon(QIcon("logo.png"))

		layout = QGridLayout(self)
		lbl = QLabel("Токен:")
		layout.addWidget(lbl, 0, 0)
		self.tokenLine = QLineEdit(self.profileData["token"])
		layout.addWidget(self.tokenLine, 0, 1)
		self.okBoomer = QPushButton("Ок")
		layout.addWidget(self.okBoomer, 1, 0, 1, 2)
		
	def __initLogic__(self):
		self.okBoomer.clicked.connect(self.accept)
		
	def exec_(self):
		super().exec_()
		return self.tokenLine.text()


class GroupsEditor(QDialog, QObject):
	
	def __init__(self, profileData):
		super().__init__()
		self.profileData = profileData
		self.__initGUI__()
		self.__initLogic__()
		
	def __initGUI__(self):
		self.setWindowTitle("Редактор групп")
		self.setWindowIcon(QIcon("logo.png"))

		layout = QGridLayout(self)
		self.addNewGroupName = QLineEdit()
		self.addNewGroupName.setPlaceholderText("Название группы")
		layout.addWidget(self.addNewGroupName, 0, 0, 1, 2)
		self.addNewGroupButton = QPushButton("Добавить группу")
		layout.addWidget(self.addNewGroupButton, 0, 2)

		hLine = QFrame()
		hLine.setFrameShape(QFrame.HLine)
		hLine.setFrameShadow(QFrame.Sunken)
		layout.addWidget(hLine, 1, 0, 1, 3)

		groupNamelbl = QLabel("Группа:")
		layout.addWidget(groupNamelbl, 2, 0)
		self.groupNameCombo = QComboBox()
		for group in self.profileData["groupsData"]:
			self.groupNameCombo.addItem(group["groupName"])
		layout.addWidget(self.groupNameCombo, 2, 1, 1, 2)

		groupIDlbl = QLabel("ID Группы:")
		layout.addWidget(groupIDlbl, 3, 0)
		self.groupIDLine = QLineEdit()
		layout.addWidget(self.groupIDLine, 3, 1, 1, 2)

		albumIDlbl = QLabel("ID Альбома:")
		layout.addWidget(albumIDlbl, 4, 0)
		self.albumIDLine = QLineEdit()
		layout.addWidget(self.albumIDLine, 4, 1, 1, 2)

		self.okBoomer = QPushButton("Ок")
		layout.addWidget(self.okBoomer, 5, 0, 1, 3)
		
	def __initLogic__(self):
		self.addNewGroupButton.clicked.connect(self.__addNewGroupFA)
		self.groupNameCombo.highlighted.connect(self.__setGroupEditForm)
		self.groupIDLine.editingFinished.connect(self.__editGroupIDFA)
		self.albumIDLine.editingFinished.connect(self.__editAlbumIDFA)
		self.okBoomer.clicked.connect(self.accept)
	
	def __addNewGroupFA(self):
		if (self.addNewGroupName.text()):
			self.profileData["groupsData"].append({})
			self.profileData["groupsData"][-1]["groupName"] = self.addNewGroupName.text()
			self.profileData["groupsData"][-1]["groupID"] = 123456789
			self.profileData["groupsData"][-1]["albumID"] = 123456789
			self.groupNameCombo.addItem(self.profileData["groupsData"][-1]["groupName"])

	def __setGroupEditForm(self, index):
		self.groupIDLine.setText(str(self.profileData["groupsData"][index]["groupID"]))
		self.albumIDLine.setText(str(self.profileData["groupsData"][index]["albumID"]))

	def __editGroupIDFA(self):
		if (self.groupIDLine.text()):
			self.profileData["groupsData"][self.groupNameCombo.currentIndex()]["groupID"] = int(self.groupIDLine.text())

	def __editAlbumIDFA(self):
		if (self.albumIDLine.text()):
			self.profileData["groupsData"][self.groupNameCombo.currentIndex()]["albumID"] = int(self.albumIDLine.text())	
		
	def exec_(self):
		super().exec_()
		self.__editGroupIDFA()
		self.__editAlbumIDFA()
		

class Program(QMainWindow):

	def __init__(self):
		super().__init__()
		self.setWindowTitle("Автопланировщик постов ВК")
		self.setWindowIcon(QIcon("logo.png"))
		self.readProfileData()
		VkConnector(self.profileData["token"])
		self.__initGUI__()
		self.__initLogic__()
		self.show()
		
	def __initGUI__(self):
		self.tabs = QTabWidget(self)
		self.addTabButton = QPushButton("+")
		self.tabs.setCornerWidget(self.addTabButton, Qt.TopRightCorner)
		self.tabs.setTabsClosable(True)
		self.actionMenu = self.menuBar().addMenu("Действия");
		self.addPlanner()
		self.setCentralWidget(self.tabs)
		
	def __initLogic__(self):
		self.addTabButton.clicked.connect(self.addPlanner)
		self.tabs.tabCloseRequested.connect(self.killPlanner)
		self.actionMenu.addAction("Изменить токен", self.editToken);
		self.actionMenu.addAction("Изменить группы", self.editGroups);
		self.actionMenu.addAction("Перезагрузить профиль", self.reloadProfileData);

	def addPlanner(self):
		index = self.tabs.count()
		planner = AutoPlanner(self.profileData)
		self.tabs.insertTab(index, planner, "Неопр. " + str(index))
		planner.groupChanged.connect(self.setPlannerTabTitle)
		self.tabs.setCurrentIndex(index)

	def setPlannerTabTitle(self, title):
		self.tabs.setTabText(self.tabs.currentIndex(), title)

	def killPlanner(self, index):
#TODO Порешай чего-нибудь с ручным удалением объектов
#gc не хочет удалять содержимое вкладки, оправдываясь сущ. ссылками
#		ConsoleIO().error(sys.getrefcount(self.tabs.widget(index)))
		self.tabs.removeTab(index)
		if (self.tabs.count() == 0):
			self.close()

	def readProfileData(self):
		ConsoleIO().log("Чтение данных профиля")
		profileDataFile = open('profileData.json', 'r', encoding = "utf-8")
		self.profileData = profileDataFile.read()
		profileDataFile.close()
		self.profileData = json.loads(self.profileData)

	def writeProfileData(self):
		ConsoleIO().log("Запись данных профиля")
		profileDataFile = open('profileData.json', 'w', encoding = "utf-8")
		profileDataFile.write(json.dumps(self.profileData, indent = 4, separators = (',', ':')))
		profileDataFile.close()
	
	def editToken(self):
		dialog = TokenEditor(self.profileData)
		token = dialog.exec_()
		if (self.profileData["token"] != token):
			self.profileData["token"] = token
			self.writeProfileData()
			self.reloadProfileData(reload=False)
	
	def editGroups(self):
		dialog = GroupsEditor(self.profileData)
		dialog.exec_()
		self.writeProfileData()
		self.reloadProfileData(reload=False)
	
	def reloadProfileData(self, reload=True):
		for index in range(0, self.tabs.count()):
			self.tabs.removeTab(0)
		if (reload):
			self.readProfileData()
		self.addPlanner()


if __name__ == '__main__':
	app = QApplication(sys.argv)
	#app.setStyle("Windows")
	program = Program()
	sys.exit(app.exec_())
