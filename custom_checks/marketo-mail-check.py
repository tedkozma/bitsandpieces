#!/usr/bin/env python

# Ted Kozma
# DESC: custom check Marketo responsiveness by generating a test payload,
# posting to Marketo, reading response in catchall mailbox and comparing. Hacky.
# 2013, Clearfit

import sys
import email
import mailbox
import re
import MySQLdb
import pytz
import datetime
import json

from optparse import OptionParser

parser = OptionParser(usage='%prog [options]', version='%prog 1.0.' + re.search('(\d+)', '$LastChangedRevision: 0001 $').group(1))

parser.add_option("-p", "--post", action="store_true", dest="Post", help="Post a new registration")
parser.add_option("-m", "--mailcheck", action="store_true", dest="Mailcheck", help="Run the mail check on catchall account")
parser.add_option("-V", "--verbose", action="store_true", dest="Verbose", default=False, help="Toggles printing extra information to the console [default: %default]")
parser.add_option("-d", "--dbcheck", action="store_true", dest="Dbcheck", help="Run the database check and generate alerts")


(options, args) = parser.parse_args()


if options.Mailcheck is None and options.Dbcheck is None and options.Post is None:
	parser.error("Options are missing\n")
	parser.print_help()


dbhost = "localhost"
dbuser = "clearfit"
dbpass = "S-E-C-R-E-T"
dbname = "marketoposts"

# for possible debugging
def dump(obj):
	  for attr in dir(obj):
			print "obj.%s = %s" % (attr, getattr(obj, attr))

# if we need to send an email
def sendalert(subject_text, email_msg):
	import smtplib
	import socket
	import time

	date = time.strftime("%Y-%m-%d", time.localtime(time.time()))
	sender = "ops@clearfit.com"
	#to = "ted.kozma@clearfit.com"
	to = "ops@clearfit.com"
	fullname = socket.gethostname()
	msg_subject = "%s - %s - %s" % (fullname, subject_text, date)
	msg_headers = "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n" % (sender, to, msg_subject)
	final_message = str(msg_headers) + str(email_msg)
	mailserver = smtplib.SMTP('127.0.0.1')
	mailserver.sendmail(sender, to, final_message)
	mailserver.quit()

try:
	conn = MySQLdb.connect( host=dbhost, user=dbuser, passwd=dbpass, db=dbname )
	cursor = conn.cursor()
except MySQLdb.OperationalError:
		print "<span class=error>Error:  %s </span>" % sys.exc_info()[1]
		sys.exit()

def post_new_registration():

	url = "http://mr.clearfit.com/syncLead"

	headers = {
		'content-type': 'application/json',
		'ORIGIN': 'https://app1.clearfit.com',
		'Access-Control-Allow-Origin': 'http://www.clearfit.com'
		}

	now = datetime.datetime.utcnow().strftime("%F %H:%M:%S")
	mboxstamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")

	currentemail = "clearfit"+mboxstamp+"@clearfit.org"

	payload = {
		'ls': 'Search Engine Marketing',
		'kw': 'TESTING STUFF',
		'ss': 'FIND TESTERS',
		'ad': '_b_FIND_TESTERS',
		'ag': 'FIND TESTERS',
		'lsn': 'this is a test',
		'lls': 'Google',
		'oot': 'Trial',
		'lot': 'Trial',
		'Industry': 'TESTING INDUSTRY',
		'opt_exp': '123456789',
		'opt_var': '123456789',
		'FirstName': 'TESTY',
		'LastName': 'TESTER',
		'Company': 'TESTINGCORP',
		'Email': currentemail,
		'ClearFit_Account_ID': 'WOR0042',
		'Phone': '333-444-555',
		'Country': 'US'
		}

	try:
		r = requests.post(url, params=payload, data=json.dumps(payload), headers=headers)
	except:
		print "Unable to post:", sys.exc_info()[0]
		sys.exit(2)

	#print dump(r)
	print r.content

	qkeys = payload.keys()
	qkeys.insert(0, 'time_registered')
	qk = str(qkeys).translate(None, "'[]")
	qvalues = payload.values()
	qvalues.insert(0, now)

	query = "INSERT INTO posts (%s) values %r;" % (qk, tuple(qvalues))
	#print query
	try:
		cursor.execute(query)
		cursor.execute("COMMIT")
		print "query executed"
	except:
		print "Unable to execute the query:"
		dump(sys.exc_info())
		sys.exit(2)

	conn.close()



def check_mail():
	try:
		conn = MySQLdb.connect( host=dbhost, user=dbuser, passwd=dbpass, db=dbname )
		cursor = conn.cursor()
	except MySQLdb.OperationalError:
			print "<span class=error>Error:  %s </span>" % sys.exc_info()
			sys.exit(1)


	mbox = mailbox.mbox("/var/mail/catchall")

	for message in mbox:
		if 'X-MarketoID' in message:
			row = ()

			# Ugly, yes, so what?
			ds = message['Date'].replace(' -0500 (CDT)', '')
			date_local = datetime.datetime.strptime(ds, "%a, %d %b %Y %H:%M:%S")
			date_local_string  = date_local.strftime("%Y-%m-%d %H:%M:%S")
			ds_utc = pytz.timezone('America/Chicago').localize(datetime.datetime.strptime(date_local_string, '%Y-%m-%d %H:%M:%S')).astimezone(pytz.utc)


			row = ( message['To'],
			message['Subject'],
			message['X-Original-To'],
			message['Received'],
			message['From'],
			ds_utc.strftime("%F %H:%M:%S"),
			message['X-MarketoID'],
			message['breadcrumbId'],
			message['X-Mailfrom'] )

			r = str(row).translate(None, "()")
			#print r

			query="REPLACE INTO deliveries values (%s);" % r
			#print query

			try:
				cursor.execute(query)
				cursor.execute("COMMIT")
				#print "insert executed"
			except:
				print "Unable to execute the query:"
				print sys.exc_info()
				sys.exit(2)

	conn.close()

def check_db():

	unresponded = {}

	try:
		conn = MySQLdb.connect( host=dbhost, user=dbuser, passwd=dbpass, db=dbname )
		cursor = conn.cursor()
	except MySQLdb.OperationalError:
			print "Unable to connect to db:  %s " % sys.exc_info()
			sys.exit(1)

	q1 = 'select *, timediff(now(), time_registered) as HowLongAgo from posts_deliveries where Date is NULL;'
	cursor.execute(q1)
	rs = cursor.fetchall()
	if rs:
		subject = "There are unanswered posts by Marketo"
		text =  "Marketo posts for following email addresses were not responded for yet:\n"
		for r in rs:
				if r[5] < datetime.timedelta(minutes = 10):
					text = text+"Post by %s registered on %s was not responded in %s\n" %(str(r[0]), str(r[1]), str(r[5]))


		print subject
		print
		print text

		sendalert(subject, text)

	conn.close()


########### Main here ##########
if __name__ == '__main__':
	if options.Mailcheck:
		check_mail()
	if options.Dbcheck:
		check_db()
	if options.Post:
		post_new_registration()


