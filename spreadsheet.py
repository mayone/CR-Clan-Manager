# -*- coding: utf-8 -*-

import pprint
import datetime
from tqdm import tqdm

import pygsheets

import crapi
import utils

from enum import IntEnum, auto


pp = pprint.PrettyPrinter()

class Color():
	# In tuple (red, green, blue, alpha)
	white = (0, 0, 0, 0)
	grey = (0.7382812, 0.7382812, 0.7382812, 0)
	red = (1, 0, 0, 0)
	blue = (0, 1, 1, 0)
	orange = (0.9647059, 0.69803923, 0.41960785, 0)
	skin = (1, 0.8980392, 0.6, 0)
	pink = (0.95686275, 0.8, 0.8, 0)
	d_green = (0.5764706, 0.76862746, 0.49019608, 0)
	d_blue = (0.6431373, 0.7607843, 0.95686275, 0)

class RecordGenre(IntEnum):
	UNKNOWN = auto()
	WAR = auto()
	DONATE = auto()

class Sheet():
	def __init__(self, index=0):
		self.__sheet = self.__open_sheet(index)
		self.__crapi = crapi.CRAPI()

	def __open_sheet(self, index):
		"""Open worksheet.

		Parameters
		----------
		index : int
		    Index of worksheet in spreadsheet (starts from 0).
		"""
		client = pygsheets.authorize(service_file='client_secret.json')

		# Open a worksheet from spreadsheet
		spreadsheet = client.open('[皇室戰爭] 部落統計')
		sheet = spreadsheet.worksheet(value=index)

		return sheet

	def __set_frozen_cols(self, num_cols):
		sheet = self.__sheet
		sheet.frozen_cols = num_cols

	def __get_tag_cells(self):
		sheet = self.__sheet
		start = sheet.find('標籤')[0].neighbour('bottom')
		end = start
		while end.neighbour('bottom').value != '':
			end = end.neighbour('bottom')

		tag_cells = [list[0] for list in sheet.range(start.label + ':' + end.label, returnas='cells')]

		return tag_cells

	def __sort_by_trophies(self, last_updated_row_index=51):
		sheet = self.__sheet

		print("Sorting by trophies...")
		# basecolumnindex starts from 0
		sheet.sort_range(
			start=(2, 1),
			end=(last_updated_row_index, sheet.cols),
			basecolumnindex=sheet.find('最高盃數')[0].col - 1,
			sortorder='DESCENDING')

		print("Sorted by trophies")

	def init(self):
		sheet = self.__sheet
		header_cells = sheet.get_row(1, returnas='cells')
		members = self.__crapi.get_members_dic().values()

		# Setup headers
		for header_cell in header_cells:
			header_cell.color = Color.grey
		header_cells[0].value = "帳號"
		header_cells[1].value = "標籤"
		header_cells[2].value = "最高盃數"
		header_cells[3].value = "職位"
		header_cells[3].note = "首領 3\n副首 2\n長老 1\n成員 0"
		sheet.adjust_column_width(start=0, pixel_size=120)
		sheet.adjust_column_width(start=2, pixel_size=60)
		sheet.adjust_column_width(start=3, pixel_size=60)
		self.__set_frozen_cols(4)

		# Add members
		self.update_members()

	def update_members(self):
		sheet = self.__sheet
		tag_cells = self.__get_tag_cells()
		members = self.__crapi.get_members_dic()

		sheet_tags = []
		insertable_row_index = tag_cells[len(tag_cells)-1].row + 1
		last_inserted_row_index = 0

		# Put none exist members in list
		member_to_remove = []
		for tag_cell in tag_cells:
			tag = tag_cell.value
			try:
				member = members[tag]
			except Exception as e:
				name = tag_cell.neighbour('left').value
				member_to_remove.append((name, tag_cell.row))
				continue
			sheet_tags.append(tag)

		# Remove none exist members in reversed order
		for member in reversed(member_to_remove):
			name = member[0]
			row_index = member[1]
			# Insert empty row in the bottom
			sheet.insert_rows(tag_cells[len(tag_cells)-1].row)
			sheet.delete_rows(row_index)
			print("Member: {0} is removed".format(
					utils.align(name, length=32)))
			insertable_row_index -= 1

		# Add new members
		tags = members.keys()
		for tag in tags:
			if tag not in sheet_tags:
				member = members[tag]
				row_to_fill = sheet.get_row(insertable_row_index, returnas='cells')
				row_to_fill[0].value = member['name']
				row_to_fill[1].value = tag
				row_to_fill[2].value = member['bestTrophies']
				role = member['role']
				if role == "leader":
					row_to_fill[3].value = "3"
					row_to_fill[3].color = Color.orange
				elif role == "coLeader":
					row_to_fill[3].value = "2"
					row_to_fill[3].color = Color.d_blue
				elif role == "elder":
					row_to_fill[3].value = "1"
					row_to_fill[3].color = Color.d_green
				elif role == "member":
					row_to_fill[3].value = "0"
				else:
					row_to_fill[3].value = "0"
				print("Member: {0} is added".format(
					utils.align(member['name'], length=32)))
				last_inserted_row_index = insertable_row_index
				insertable_row_index += 1

		if last_inserted_row_index > 0:
			self.__sort_by_trophies(last_inserted_row_index)

	def update_trophies(self):
		sheet = self.__sheet
		tag_cells = self.__get_tag_cells()
		members = self.__crapi.get_members_dic()
		last_updated_row_index = 0

		print("Updating trophies...")

		for tag_cell in tag_cells:
			tag = tag_cell.value
			try:
				member = members[tag]
			except Exception as e:
				print("Warning: member tag " + tag + " do not exists")
				continue
			trophy_cell = tag_cell.neighbour('right')
			if trophy_cell.value < str(member['bestTrophies']):
				print("Update member {0} trophies: {1} -> {2}".format(
						utils.align(member['name'], length=32),
						trophy_cell.value, member['bestTrophies']))
				trophy_cell.value = str(member['bestTrophies'])
				last_updated_row_index = trophy_cell.row

		if last_updated_row_index > 0:
			self.__sort_by_trophies(last_updated_row_index)
			print("Trophies updated")
		else:
			print("Trophies are already up to date")

	def update_warlog(self):
		sheet = self.__sheet
		header_cells = sheet.get_row(1, returnas='cells')

		# Search and set latest updated (genre, date, col_offset)
		latest_updated_genre = RecordGenre.UNKNOWN
		for header_cell in reversed(header_cells):
			if header_cell.note != None:
				try:
					if header_cell.note.split()[0] == "發起日":
						latest_updated_genre = RecordGenre.WAR
					elif header_cell.note.split()[0] == "統計日":
						latest_updated_genre = RecordGenre.DONATE
					latest_updated_date = header_cell.note.split()[1]
					latest_updated_col_offset = sheet.cols - header_cell.col
					break
				except Exception as e:
					continue

		if latest_updated_genre == RecordGenre.UNKNOWN:
			latest_updated_col_offset = sheet.cols - 4
			latest_updated_date = "00000000"

		warlog = self.__crapi.get_warlog()
		warlog_unrecorded_offset = -1

		# Set index to the unrecorded war in warlog
		for i in range(len(warlog)):		
			war = warlog[i]
			date = utils.get_date_str(
					utils.utc_to_local(
						utils.datetime_from_str(war['createdDate'])))
			if date > latest_updated_date:
				warlog_unrecorded_offset = i
			elif date == latest_updated_date and \
				latest_updated_genre == RecordGenre.DONATE:
				warlog_unrecorded_offset = i
			else:
				break

		for i in range(warlog_unrecorded_offset, -1, -1):
			war = warlog[i]
			# Keep the last column empty
			if latest_updated_col_offset <= 1:
				# insert and inherit from the last column
				sheet.insert_cols(sheet.cols - 1, number=1, values=None, inherit=False)
				latest_updated_col_offset += 1
			self.__update_war(latest_updated_col_offset - 1, war)
			latest_updated_col_offset -= 1

		return True

	def __update_war(self, col_offset, war):
		"""Update specified war records to the target column.

		Parameters
		----------
		col_offset : int
		    Offset of the target column from the last column.
		war: Object
		    The war from the warlog to be recorded
		"""
		sheet = self.__sheet
		col_index = sheet.cols - col_offset
		tag_cells = self.__get_tag_cells()

		# Get info from warlog
		date = war['createdDate'].split('T')[0]
		participants = war['participants']
		standings = war['standings']
		for standing in standings:
			if standing['clan']['tag'] == crapi.clan_tag:
				trophy_change = standing['trophyChange']
				break

		print("Updating war " + date)

		header_cell = sheet.cell((1, col_index))
		header_cell.value = "部落戰 " + str(trophy_change)
		header_cell.note = "發起日 " + date
		header_cell.color = Color.pink

		# Fill war records into sheet
		for p in tqdm(participants):
			tag = p['tag']
			row_index = 0
			for tag_cell in tag_cells:
				if tag == tag_cell.value:
					row_index = tag_cell.row
					break
			if row_index:
				cell = sheet.cell((row_index, col_index))
			else:
				print("Warning: member tag " + tag + " do not exists")
				continue

			warday_played = p['battlesPlayed']
			wins = p['wins']
			loses = warday_played - wins

			# Form record and fill in
			record = ""
			record += str(p['cardsEarned'])
			record += 'L' * loses
			record += 'w' * wins
			if warday_played == 0:
				record += "x"
			cell.value = record

			# Mark with color red if didn't complete all battles
			if warday_played == 0 or p['collectionDayBattlesPlayed'] < 3:
				cell.color = Color.red
				if (p['collectionDayBattlesPlayed'] < 3):
					cell.note = "收集日({0}/3)".format(p['collectionDayBattlesPlayed'])

	def update_donations(self, date=None, delay=None):
		sheet = self.__sheet
		tag_cells = self.__get_tag_cells()
		members = self.__crapi.get_members_dic()

		header_cells = sheet.get_row(1, returnas='cells')

		# Search and set latest updated (genre, date, col_offset)
		latest_updated_genre = RecordGenre.UNKNOWN
		for header_cell in reversed(header_cells):
			if header_cell.note != None:
				try:
					if header_cell.note.split()[0] == "發起日":
						latest_updated_genre = RecordGenre.WAR
					elif header_cell.note.split()[0] == "統計日":
						latest_updated_genre = RecordGenre.DONATE
					latest_updated_date = header_cell.note.split()[1]
					latest_updated_col_offset = sheet.cols - header_cell.col
					break
				except Exception as e:
					continue

		now = utils.get_now()
		if date:
			record_dt = datetime.datetime(now.year, int(date.split('/')[0]), int(date.split('/')[1]))
			full_date = utils.get_date_str(record_dt)
		else:
			date = now.strftime("%m/%d")
			full_date = utils.get_date_str(now)

		if latest_updated_date == full_date and \
			latest_updated_genre == RecordGenre.DONATE:
			# Update the existed record
			col_index = sheet.cols - latest_updated_col_offset
		else:
			# Keep the last column empty
			if latest_updated_col_offset <= 1:
				# insert and inherit from the last column
				sheet.insert_cols(sheet.cols - 1, number=1, values=None, inherit=False)
				latest_updated_col_offset += 1
			# Record in new coulumn
			col_offset = latest_updated_col_offset - 1
			col_index = sheet.cols - col_offset

		header_cell = sheet.cell((1, col_index))
		header_cell.value = "捐贈 " + date
		header_cell.note = "統計日 " + full_date
		header_cell.color = Color.skin

		print("Updating donations " + date)

		# Update donations of each member
		for tag_cell in tqdm(tag_cells):
			tag = tag_cell.value
			try:
				member = members[tag]
			except Exception as e:
				print("Warning: member tag " + tag + " do not exists")
				continue

			row_index = tag_cell.row

			cell = sheet.cell((row_index, col_index))
			cell.value = str(member['donations'])

	def __print_all(self):
		sheet = self.__sheet
		result = sheet.get_all_values(include_tailing_empty_rows=False)
		pp.pprint(result)