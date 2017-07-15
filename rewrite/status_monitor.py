
#pylint: disable-msg=F0401, W0142

from settings import settings

import logging
import psycopg2
import traceback


class DbInterface(object):

	def __init__(self):

		self.log = logging.getLogger("Main.DbInterface")
		self.openDB()

	def __del__(self):
		self.closeDB()


	def openDB(self):
		self.log.info("StatusManager Opening DB...")

		self.conn = psycopg2.connect(
			database = settings["postgres"]['database'],
			user     = settings["postgres"]['username'],
			password = settings["postgres"]['password'],
			host     = settings["postgres"]['address']
			)



	def closeDB(self):
		self.log.info("Closing DB...",)
		try:
			self.conn.close()
		except:
			self.log.error("wat")
			self.log.error(traceback.format_exc())
		self.log.info("done")


class StatusResource(DbInterface):


	def __init__(self):
		super().__init__()

		self.log = logging.getLogger("Main.StatusMgr")
		self.checkInitStatusDatabase()

	def checkInitStatusDatabase(self):

		cur = self.conn.cursor()
		ret = cur.execute('''
				SELECT table_name
				FROM information_schema.tables
				WHERE table_schema='public'
				ORDER BY table_schema,table_name;
			''')

		rets = cur.fetchall()
		tables = [item for sublist in rets for item in sublist]
		print("rets:", rets)
		print("tables:", tables)

		if not rets or not "statusdb" in tables:   # If the DB doesn't exist, set it up.
			cur = self.conn.cursor()
			self.log.info("Need to setup initial suceeded page database....")
			cur.execute('''CREATE TABLE statusdb (
												id          serial primary key,
												siteName    text NOT NULL,
												sectionName text NOT NULL,
												statusText  text,
												UNIQUE(siteName, sectionName))''')

			cur.execute('''CREATE INDEX statusDb_site_section_index ON statusdb (siteName, sectionName)''')

			cur.execute("commit")
			self.log.info("Status database created")



	def updateValue(self, sitename, key, value):
		cur = self.conn.cursor()
		cur.execute("""SELECT id FROM statusdb WHERE sitename=%s AND sectionName=%s;""", (sitename, key))
		ret = cur.fetchone()

		# print((sitename, key, value, ret))
		if ret and len(ret) > 0:
			dbid = ret[0]
		else:
			dbid = None

		if dbid:
			cur.execute("""UPDATE statusdb SET statusText=%s WHERE id=%s""", (str(value), dbid))
		else:
			cur.execute('''INSERT INTO statusdb (siteName, sectionName, statusText) VALUES (%s, %s, %s);''', (sitename, key, value))
		cur.execute("COMMIT;")

	def updateNextRunTime(self, name, timestamp):
		self.updateValue(name, "nextRun", timestamp)

	def updateLastRunStartTime(self, name, timestamp):
		self.updateValue(name, "prevRun", timestamp)

	def updateLastRunDuration(self, name, timeDelta):
		self.updateValue(name, "prevRunTime", timeDelta)

	def updateRunningStatus(self, name, state):
		self.updateValue(name, "isRunning", state)


class DbUpgrader(DbInterface):


	def checkUpgradeR1(self):
		table_info_query = '''
			SELECT column_name FROM information_schema.columns
			WHERE table_name = '{table_name}';
		'''.format(table_name=settings["dbConf"]["namesDb"])

		cur = self.conn.cursor()
		cur.execute(table_info_query)
		dat = cur.fetchall()
		cols = [tmp[0] for tmp in dat]
		for col in dat:
			print(col)
		print(cols)

		if not 'last_fetched' in cols:
			print("Need to add column!")
			cur.execute('''
					ALTER TABLE
						{table_name}
					ADD COLUMN last_fetched double precision default 0;
				'''.format(table_name=settings["dbConf"]["namesDb"]))
			cur.execute("COMMIT;")

	def go(self):
		self.checkUpgradeR1()


def go():
	wat = StatusResource()
	print(wat)


def db_upgrade():
	d = DbUpgrader()
	d.go()

if __name__ == "__main__":
	go()
