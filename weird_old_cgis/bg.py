#!/usr/bin/python
# -*- coding: utf-8 -*-

# Ted Kozma
#DESC::: Checks status of a background tasks or enable a background task. Note: password required in order to enable a task.
# 2010

import sys
import re
import os
import MySQLdb
import time
import cgitb; cgitb.enable()
#import pxssh
import smtplib
import cgi
#from SOAPpy import WSDL
from time import sleep

# global vars
base_url = "http://10.63.10.25/tools/bg.py"

dcmap = {'EU': {'custsto': '10.215.10.11', 'monbox': '10.215.10.251','directory': '10.215.10.51'},
	'BRA': {'custsto': '10.98.10.11', 'monbox': '10.98.53.251','directory': '10.98.53.52'},
	'Tor6': {'custsto': '10.130.64.13', 'monbox': '10.98.10.254','directory': '10.98.10.51'},
	'US2': {'custsto': '10.102.10.17', 'monbox': '10.102.11.254','directory': '10.102.10.52'}}

# Added yavila as per PROD-1025
allowed_to_enable = ['tkozma', 'araileanu', 'jvaldez', 'vadhopia', 'epfefferle', 'mhart', 'sprokai', 'zkedzior', 'yavila', 'ctebo']

form = cgi.FieldStorage()

def page_header(current):
	print "Content-Type: text/html\n"
	print "<HTML>"
	print "<HEAD>"
	print "<SCRIPT TYPE=\"text/javascript\">\n"
	print "<!--\n"
	print "function dropdown(mySel)\n"
	print "{\n"
	print "var myWin, myVal;\n"
	print "myVal = mySel.options[mySel.selectedIndex].value;\n"
	print "if(myVal)\n"
	print "{\n"
	print "if(mySel.form.target)myWin = parent[mySel.form.target];\n"
	print "else myWin = window;\n"
	print "if (! myWin) return true;\n"
	print "myWin.location = myVal;\n"
	print "}\n"
	print "return false"
	print "}\n"
	print "//-->\n"
	print "</SCRIPT>\n"
	print "<link href=\"http://10.63.10.25/ccd/ccd.css\" rel=\"stylesheet\" type=\"text/css\">"
	print "</HEAD>"

	# creating logo at top of page

	print "<BODY BGCOLOR=#FFFFFF leftmargin=0 topmargin=0>"
	print "<table border=0 width=\"90%\" cellpadding=5 cellspacing=5>"
	print "<tr>"
	print "<td align=\"left\" valign=\"bottom\">"
	print "<table border=\"0\" width=\"90%\" cellpadding=\"5\" cellspacing=\"5\">"
	print "<tr>"
	print "<td valign=\"top\" align=\"left\">"
	print "<img src=\"http://10.63.10.25/ccd/proofpoint_logo_17.gif\" alt=\"Top left corner\" border=\"0\">"
	print "</td>"
	print "</tr>"
	print "</table>"
	print "<br>"
	print "<table width=\"100%\" border=\"0\" cellpadding=\"5\" cellspacing=\"5\" style=\"PADDING-LEFT: 5px\">"
	print "<tr>"
	print "<td align=\"left\" colspan=\"2\">"
	print "<span class=maintitle>Proofpoint Archiving - Background tasks management, v1.0</span><br>"
	print "<br>"

	menu_dict = {}
	menu_dict = {'set_retries': 'SET AUTOMATIC RETRIES', 'task_status': 'VIEW TASK STATUS', 'task_enable': 'ENABLE TASK'}

	print "<table id=\"navbar\"> "

	for key in menu_dict.keys():
	  if key == current:
	    print "<TR><TD><A HREF=\"%s?option=%s\">  [%s]  </A></TD></TR>" %(base_url,key,menu_dict[key])
	  else:
	    print "<TR><TD><A HREF=\"%s?option=%s\">  %s  </A></TD></TR>" %(base_url,key,menu_dict[key])
	print "</table>"

def task_status_page():
	HTML_TEMPLATE = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
	<title>Task Status</title>
	<body>

	<form name="task_status" action="%(SCRIPT_NAME)s" method="POST" enctype="multipart/form-data">

	<table border=0>
	<tr><td>Customer GUID:</td><td colspan=4><input name="client_guid" type="text" size="50"></td></tr>
	<tr><td>Task Id (leave empty to view all tasks):&nbsp;&nbsp;&nbsp;</td><td colspan=4><input name="task_id" type="text" value="" size="30"></td></tr>

	<tr><td colspan=5><h3>Select the datacenter below</h3></td></td></tr>
	<tr><td>TOR6</td><td><input name="dc" value="Tor6" type="radio"></td></tr>
	<tr><td>Brampton</td><td><input name="dc" value="Brampton" type="radio"></td></tr>
	<tr><td>US</td><td><input name="dc" value="US2" type="radio" checked></td></tr>
	<tr><td>Europe</td><td><input name="dc" value="EU" type="radio"></td></tr>
	<tr><td>NOT SURE</td><td><input name="dc" value="DONTKNOW" type="radio"></td></tr>
	<tr><td>&nbsp;</tr>
	</table>

	<br>
	<input name="gettask" value="Get task status" type="submit">
	</form>
	</body>
	</html>"""
	print HTML_TEMPLATE % {'SCRIPT_NAME':os.environ['SCRIPT_NAME']}


def task_enable_page():
	HTML_TEMPLATE = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
	<title>Task Status</title>
	<body>

	<br>
        <p><h2>Attention!<br>Prior to enabling the task please check the table below.<br>Only re-enable those tasks that <b>"can be reprocessed"</b></h2><p>

	<table border=1 cellspacing=0 cellpadding=7>
        <tr >
        <th>Category
        </th><th>Typical Error Message
        </th><th>Can Be Reprocessed?
        </th></tr>

        <tr><td>Active Index 15 Query Retry </td><td>Attempted 15 retries of query +(((+(.....)) (+(.....))) (+(.....))) +(+(+(((d
        </td><td>Yes</td></tr>
        <tr><td>Dropped Connections</td><td>Failed to read response from async client.  </td><td>Yes</td></tr>
        <tr><td>Aborted Batches</td><td>Batch with guid hold-1_80027211986643af_111a775_129e0fdf4cc__50a7 has been aborted. Hold processing blocked.</td><td class=error>No </td></tr>
        <tr><td>Value 1&nbsp;!= 2</td><td>Value (1) should be equal to 2</td><td class=error>No</td></tr>

        <tr>
        <td>Couldn't find folder for ARL</td><td>&nbsp;</td><td class=error>No, delete these</td></tr>
        <tr><td>Prepared statement caught exception</td><td>Prepared statement caught exception.</td><td>Yes</td></tr>
        <tr><td>NullPointerException</td><td>Caught exception when processing at &lt;IP Address &amp; Port&gt;: null</td><td>Yes</td></tr>
        <tr><td>Caught SQLException</td><td>&nbsp</td><td>Yes</td></tr>
        <tr><td>Unread Block Data</td><td>Caught exception when processing at 10.102.10.24:8220: unread block data</td><td class=error>No</td></tr>
        </table>
        <br>
        <br>

        <script type="text/javascript" language="JavaScript">
          function nameempty() {
            if ( document.task_enable.password.value == '' ) {
              alert('Password required!')
              document.task_enable.password.focus();
              return false;
            }
          }
        </script>

        <form name="task_enable" onsubmit="return nameempty(this)" action="%(SCRIPT_NAME)s" method="POST" enctype="multipart/form-data">

        <table border=0 >

		<tr><td colspan=5><h3>Enter customer guid and task ID:</h3></td></td></tr>
        <tr><td>Customer GUID:</td><td colspan=4><input name="client_guid" type="text" size="60"></td></tr>
		<tr><td>Task Id<br>(comma-separated for multiple tasks):</td><td colspan=4><input name="task_id" type="text" size="60"></td></tr>

		<tr><td colspan=5><h3>Select the datacenter</h3></td></td></tr>
        <tr><td>TOR6</td><td><input name="dc" value="Tor6" type="radio"></td></tr>
        <tr><td>Brampton</td><td><input name="dc" value="Brampton" type="radio"></td></tr>
        <tr><td>US</td><td><input name="dc" value="US2" type="radio" checked></td></tr>
        <tr><td>Europe</td><td><input name="dc" value="EU" type="radio"></td></tr>
        <tr><td>NOT SURE</td><td><input name="dc" value="DONTKNOW" type="radio"></td></tr>
        <tr><td>&nbsp;</tr>

        <tr><td>Your AD Username</td><td><input name="username" type="text"></td></tr>
        <tr><td>Password</td><td><input name="password" type="password"></td></tr>

        </table>

	<br>
	<input name="enabletask" value="Enable task" type="submit">
	</form>
	</body>
	</html>"""

	print HTML_TEMPLATE % {'SCRIPT_NAME':os.environ['SCRIPT_NAME']}

def set_retries_page():
	HTML_TEMPLATE = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
	<title>Set automatic BG task retries number</title>
	<body>
	  <script type="text/javascript" language="JavaScript">
          function nameempty() {
            if ( document.task_enable.password.value == '' ) {
              alert('Password required!')
              document.task_enable.password.focus();
              return false;
            }
          }
        </script>

        <form name="set_retries" onsubmit="return nameempty(this)" action="%(SCRIPT_NAME)s" method="POST" enctype="multipart/form-data">
        <br><br>
        <table border=0 >

		<tr><td colspan=5><h3>Enter customer guid and task ID and number of retries:</h3></td></td></tr>
        <tr><td>Customer GUID:</td><td colspan=4><input name="client_guid" type="text" size="60"></td></tr>
		<tr><td>Task Id<br>(comma-separated for multiple tasks):</td><td colspan=4><input name="task_id" type="text" size="60"></td></tr>
		<tr><td>Number of retries:</td><td colspan=4><input name="nretries" type="text" size="20"></td></tr>

		<tr><td colspan=5><h3>Select the datacenter</h3></td></td></tr>
        <tr><td>MARK</td><td><input name="dc" value="Tor6" type="radio"></td></tr>
        <tr><td>BRA</td><td><input name="dc" value="Brampton" type="radio"></td></tr>
        <tr><td>US</td><td><input name="dc" value="US2" type="radio" checked></td></tr>
        <tr><td>EU</td><td><input name="dc" value="EU" type="radio"></td></tr>
        <tr><td>NOT SURE</td><td><input name="dc" value="DONTKNOW" type="radio"></td></tr>
        <tr><td>&nbsp;</tr>

        <tr><td>Your AD Username</td><td><input name="username" type="text"></td></tr>
        <tr><td>Password</td><td><input name="password" type="password"></td></tr>

        </table>

	<br>
	<input name="setretries" value="Enable task" type="submit">
	</form>
	</body>
	</html>"""

	print HTML_TEMPLATE % {'SCRIPT_NAME':os.environ['SCRIPT_NAME']}

def find_datacenter(guid):
	db = MySQLdb.connect(host="10.63.15.25",
		user="fortro",
		passwd="S-E-C-R-E-T",
		db="dashboard2")
	cursor = db.cursor()

	query = """select d.datacenter_guid from datacenters d, datacenter_services ds, customers c
	where c.service_id = ds.id and ds.datacenter_id = d.id  and c.customer_guid = '"""+guid+"';"

	cursor.execute(query)
	rs = cursor.fetchone()
	if rs is None:
	  return "NOTFOUND"
	else:
	  datacenter = rs[0]
	  return datacenter
	db.close()

def find_customer_name(guid):
	db = MySQLdb.connect(host="10.63.15.25",
		user="fortro",
		passwd="S-E-C-R-E-T",
		db="dashboard2")
	cursor = db.cursor()
	query = """select c.customer_name from customers c
		where c.customer_guid = '"""+guid+"';"
	cursor.execute(query)
	rs = cursor.fetchone()
	if rs is None:
		return "NOTFOUND"
	else:
		customer_name = rs[0]
		return customer_name
	db.close()

def task_status(guid,datacenter,task_id):
	if datacenter == 'DONTKNOW':
	  datacenter = find_datacenter(guid)
	  if datacenter == 'NOTFOUND':
	     print "<span class=\"error\"><h3>Could not determine the datacenter for the customer %s <br>" % guid
	     print "Please verify the customer guid</span>"
	     sys.exit()
	  else:
	    print "<p><b>Found your customer %s in the %s datacenter</b></p>" % (guid,datacenter)

	customer_name = find_customer_name(guid)
	monbox = dcmap[datacenter]['monbox']
	cmdurl = "http://%s:8086/aux/Bg.pl" % monbox

	print """<p><b><font color = olive>NOTE:</font> Ignore exceptions like:</b><br>
		"An exception was thrown while trying to connect to the service at: %s:8204"<br>
		</p>""" % monbox

	if task_id == "":
		cmdurl = "%s?guid=%s&action=view" %(cmdurl,guid)
		print cmdurl,"<br>"
		print "<p><h3>Status of all tasks for customer %s in %s datacenter:</h3></p>" %(customer_name,datacenter)

	else:
		cmdurl = "%s?guid=%s&taskid=%s&action=view" %(cmdurl,guid,task_id)
		print "<p><h3>Status of task %s for customer %s in %s datacenter:</h3></p>" %(task_id,customer_name,datacenter)

 #	cmd = "curl -sNf \'http://%s:8086/aux/Bg.pl?guid=%s&action=view\' 2>&1" %(monbox,guid)
	cmd = "curl -sNf \'%s\' 2>&1" % cmdurl
	out = os.popen(cmd).read()

	print "<table width=\"80%\" border=1>"
 	print "<tr><td><pre>%s</pre></td></tr>" %out
	print "</table>"

def email(SUBJ,TEXT):
	#SENDMAIL = '/usr/sbin/sendmail'
	SERVER = 'localhost'
	FROM = 'archiving-sysadmin@proofpoint.com'
	TO = 'x-legalholdprocessing@proofpoint.com'
	#TO = 'tkozma@proofpoint.com'
	SUBJECT = SUBJ

	from time import strftime
	TIMESTAMP = strftime("%Y-%m-%d %H:%M")
	#cmd = "/usr/bin/fortune -sa"
	#FORT = os.popen(cmd).read()

	message = """\
From: %s
To: %s
Subject: %s

Message from BG task tool at 10.63.10.25.
The time is %s EDT

%s

""" %(FROM, TO, SUBJ, TIMESTAMP, TEXT)

	server = smtplib.SMTP(SERVER)
	server.sendmail(FROM, TO, message)
	server.quit


def auth(user,passwd):
	import ldap
	server = '10.63.10.21'
	basedn = "dc=proofpoint,dc=com"
	server = "ldap://%s:3268" % server
	filter = "(|(uid=" + user + "*)(mail=" + user + "*))"

	auth_result = [0, 'UNKNOWN']
	l=ldap.initialize(server)

	l.set_option(ldap.OPT_REFERRALS, 0)

	try:
		l.bind("corp\\"+user, passwd)
		auth_result[0] = 1

	except ldap.INVALID_CREDENTIALS:
		auth_result[0] = 0

	results = l.search_s(basedn,ldap.SCOPE_SUBTREE,filter)

	dn_arr = []
	for dn,entry in results:
		dn = str(dn)
		dn_arr.append(dn)

	if len(dn_arr) != 1:
		auth_result = [0, 'INTRUDER']
	else:
		auth_result = [1, dn_arr[0].split(",")[0]]

	return auth_result
	l.unbind_s()


def task_enable(guid,datacenter,task_id,username,password):

	customer_name = find_customer_name(guid)
	monbox = dcmap[datacenter]['monbox']

	if username not in allowed_to_enable:
		subj = "Notification: BG task enabler login failed"
		text = "User %s, not allowed to use BG task enabler\nTried to enable task %s for customer %s (%s)" % (username, task_id, guid, customer_name)
		email(subj,text)
		print "<span class=error>User <b>%s</b> is not allowed to use the task enabler</span>" % username
		sys.exit()

	try:
		auth_result = auth(username, password)
		if auth_result[0] == 1:
			print "<br><font color=olive>Authenticated as <b>%s</b>, proceeding</font><br>" %auth_result[1].strip("CN=")
		else:
			subj = "Notification: BG task manager login failed"
			text = "User %s failed to login as %s\nwhen trying to enable task %s for customer %s (%s)" % (auth_result[1], username, task_id, guid, customer_name)
			email(subj,text)
			print "Failed to authenticate %s<br>" % auth_result[1]
			sys.exit()

	except:
		print "<tr><td class=error>Could not authenticate %s<br>Please check your login and try again</td></tr>" % username
		print "<br>"

		subj = "Notification: BG task enabler login failed"
		text = "User %s failed to login when trying to enable task %s for %s" % (username, task_id, guid)
		email(subj,text)
		sys.exit()

	if datacenter == 'DONTKNOW':
		datacenter = find_datacenter(guid)
		if datacenter == 'NOTFOUND':
			print "<span class=\"error\"><h3>Could not determine the datacenter for the customer %s <br>" % guid
			print "Please verify the customer guid</span>"
			sys.exit()
		else:
			print "<p><b>Found your customer %s in the %s datacenter</b></p>" % (guid,datacenter)


	if task_id == "":
		print "<span class=error><b>Task ID required!</b></span>"
		sys.exit()

	tasks = task_id.split(",")
	print """<p><b><font color = olive>NOTE:</font> Ignore exceptions like:</b><br>
		"An exception was thrown while trying to connect to the service at: %s:8204"<br>
		</p>""" % monbox

	for t in tasks:
		t = t.strip()
		cmd = "curl -sNf \'http://%s:8086/aux/Bg.pl?guid=%s&taskid=%s&action=enable\'" %(monbox,guid,t)

		print "<table width=\"80%\" border=1>"
		print "<tr><td> <b>Enabling task %s for customer %s </b></td></tr>" % (t,guid)

		out = os.popen(cmd).read()
		print "<tr><td><pre>%s</pre></td></tr>" %out
		#print "<tr><td><pre>%s</pre></td></tr>" %cmd


		print "</table>"

	subj = "Notification: BG task enabled"
	text = "User %s logged in and enabled tasks %s for %s (%s) in %s datacenter" % (username, task_id, guid, customer_name, datacenter)
	email(subj,text)

	print "</BODY></HTML>"

def set_retries(guid,datacenter,task_id,nretries,username,password):

	customer_name = find_customer_name(guid)
	monbox = dcmap[datacenter]['monbox']

	if username not in allowed_to_enable:
		subj = "Notification: BG task enabler login failed"
		text = "User %s, not allowed to use BG task enabler\nTried to enable task %s for customer %s (%s)" % (username, task_id, guid, customer_name)
		email(subj,text)
		print "<span class=error>User <b>%s</b> is not allowed to use the task enabler</span>" % username
		sys.exit()

	try:
		auth_result = auth(username, password)
		if auth_result[0] == 1:
			print "<br><font color=olive>Authenticated as <b>%s</b>, proceeding</font><br>" %auth_result[1].strip("CN=")
		else:
			subj = "Notification: BG task manager login failed"
			text = "User %s failed to login as %s\nwhen trying to set automatic retries to %s for task %s,  customer %s (%s)" % (auth_result[1], username, nretries, task_id, guid, customer_name)
			email(subj,text)
			print "Failed to authenticate %s<br>" % auth_result[1]
			sys.exit()

	except:
		print "<tr><td class=error>Could not authenticate %s<br>Please check your login and try again</td></tr>" % username
		print "<br>"

		subj = "Notification: BG task enabler login failed"
		text = "User %s failed to login as %s\nwhen trying to set automatic retries to %s for task %s,  customer %s (%s)" % (auth_result[1], username, nretries, task_id, guid, customer_name)
		email(subj,text)
		sys.exit()

	if datacenter == 'DONTKNOW':
		datacenter = find_datacenter(guid)
		if datacenter == 'NOTFOUND':
			print "<span class=\"error\"><h3>Could not determine the datacenter for the customer %s <br>" % guid
			print "Please verify the customer guid</span>"
			sys.exit()
		else:
			print "<p><b>Found your customer %s in the %s datacenter</b></p>" % (guid,datacenter)

	if task_id == "":
		print "<span class=error><b>Task ID required!</b></span>"
		sys.exit()

	# if task_id.isdigit():
		# print "<span class=error><b>Task ID expected to be an integer!</b></span>"
		# sys.exit()

	if not nretries.isdigit():
		print "<span class=error><b>Number of retries expected to be an integer!</b></span>"
		sys.exit()

	print """<p><b><font color = olive>NOTE:</font> Ignore exceptions like:</b><br>
		"An exception was thrown while trying to connect to the service at: %s:8204"<br>
		</p>""" % monbox

	tasks = task_id.split(",")
	for t in tasks:
		t = t.strip()
		cmd = "curl -sNf 'http://%s:8086/aux/Bg.pl?guid=%s&taskid=%s&nretries=%s&action=setretries'" %(monbox,guid,t,nretries)

		print "<table width=\"80%\" border=1>"
		print "<tr><td> <b>Will set %s automatic retries for task %s for customer %s </b></td></tr>" % (nretries,t,guid)

		out = os.popen(cmd).read()
		print "<tr><td><pre>%s</pre></td></tr>" %out
		#print "<tr><td><pre>%s</pre></td></tr>" %cmd

		print "</table>"

	subj = "Notification: BG task automatic retries set"
	text = "User %s logged in and set automatic retries to %s for the tasks %s for customer %s (%s) in %s datacenter" % (username, nretries, task_id, guid, customer_name, datacenter)
	email(subj,text)

	print "</BODY></HTML>"

def master_control():
	if ( form.has_key("option") ):
		if ( (form["option"].value == "task_enable") ):
			page_header("task_enable")
			task_enable_page()
		elif ( (form["option"].value == "set_retries") ):
			page_header("set_retries")
			set_retries_page()
		else:
			page_header("task_status")
			task_status_page()

	elif ( form.has_key("gettask") ):
		page_header("task_status_page")
		task_status(form["client_guid"].value.strip(), form["dc"].value.strip(),form.getvalue("task_id").strip())

	elif ( form.has_key("enabletask") ):
		page_header("task_enable_page")
		task_enable(form["client_guid"].value.strip(), form["dc"].value.strip(),form.getvalue("task_id").strip(),form.getvalue("username").strip(),form.getvalue("password").strip())

	elif ( form.has_key("setretries") ):
		page_header("set_retries_page")
		set_retries(form["client_guid"].value.strip(), form["dc"].value.strip(),form.getvalue("task_id").strip(),form.getvalue("nretries").strip(),form.getvalue("username").strip(),form.getvalue("password").strip())
	else:
		page_header("task_status")
		task_status_page()

master_control()
