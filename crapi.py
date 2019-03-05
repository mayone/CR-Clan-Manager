# -*- coding: utf-8 -*-

import json
import requests
import urllib
try:
	# python 2
	from urllib import quote_plus
except ImportError:
	# python 3
	from urllib.parse import quote_plus

import utils


clan_tag = "#8V8CCV"

class CRAPI():
	def __init__(self):
		with open('crapi.json') as api_file:
			api = json.load(api_file)
		api_token = api['key']
		headers = {
				'Accept': 'application/json',
				'authorization': 'Bearer' + ' ' + api_token}
		self.__base_url = "https://api.clashroyale.com/" + api['version']
		self.__session = requests.session()
		self.__session.headers.update(headers)

	def __send_req(self, query):
		session = self.__session

		req = self.__base_url + query
		try:
			resp = session.get(req)
		except Exception as e:
			print(e)
			return None

		if resp.status_code == 200:
			data = resp.json()
			return data
		else:
			print("Error: " + resp.status_code)
			return None

	def get_members(self):
		"""Get members of the clan.

		Returns
		-------
		members : dictionary
		    Use tag as key, member as value.
		"""
		query = "/clans/{0}".format(quote_plus(clan_tag)) + "/members"
		members = self.__send_req(query)['items']
		hash_members = {}

		for member in members:
			query = "/players/{0}".format(quote_plus(member['tag']))
			player = self.__send_req(query)
			# Add field 'bestTrophies' to each member
			member['bestTrophies'] = player['bestTrophies']
			hash_members[member['tag']] = member

		return hash_members

	def show_members(self):
		members = list(self.get_members().values())
		print("部落成員，共 {0} 名".format(len(members)))
		print("{0}{1}{2}{3}".format(
					utils.align("排名", length=6),
					utils.align("名字", length=32),
					utils.align("職位", length=6),
					utils.align("獎盃", length=4)))
		print("=" * 48)
		for member in members:
			tag = member['tag']
			name = member['name']
			role = member['role']
			if role == "leader":
				role = "首領"
			elif role == "coLeader":
				role = "副首"
			elif role == "elder":
				role = "長老"
			elif role == "member":
				role = "成員"
			else:
				role = role
			clan_rank = str(member['clanRank'])
			trophies = str(member['trophies'])

			print("{0}{1}{2}{3}".format(
						utils.align(clan_rank, length=6),
						utils.align(name, length=32),
						utils.align(role, length=6),
						utils.align(trophies, length=4)))

	def get_warlog(self):
		"""Get warlog of the clan.

		Returns
		-------
		warlog : list
		    Order: later to former.
		"""
		query = "/clans/{0}".format(quote_plus(clan_tag)) + "/warlog"
		warlog = self.__send_req(query)['items']

		return warlog

	def show_warlog(self, count=0):
		warlog = self.get_warlog()
		if count > 0:
			# If count is specified, only show that amount of war
			warlog = warlog[0:count]

		print("部落戰紀錄 {0} ~ {1}，共 {2} 筆".format(
			warlog[len(warlog)-1]['createdDate'].split('T')[0],
			warlog[0]['createdDate'].split('T')[0],
			len(warlog)))
		print("=" * 48)
		for war in reversed(warlog):
			date = war['createdDate'].split('T')[0]
			participants = war['participants']
			standings = war['standings']
			for standing in standings:
				if standing['clan']['tag'] == clan_tag:
					trophy_change = standing['trophyChange']
			print("部落戰 {0}".format(date))
			print("獎盃： {0}".format(trophy_change))
			print("參加人數： {0}".format(len(participants)))
			print("名單：", end='')
			i = 0
			for p in participants:
				if i % 3 == 0:
					print("\n\t", end='')
				print("{0}".format(utils.align(p['name'], length=20)), end='')
				i += 1
			print("")
			print("=" * 48)