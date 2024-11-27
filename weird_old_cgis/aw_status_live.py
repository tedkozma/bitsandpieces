#!/usr/bin/python
# -*- coding: utf-8 -*-

# Ted Kozma
#DESC::: Status of Archive Writers in all datacentres. Live, so it may take a while to load.
# 2010

import sys #,traceback
#sys.stderr = sys.stdout
import re
import os
import MySQLdb
import cgitb; cgitb.enable()
import cgi
from time import sleep

# global vars
base_url = "http://10.63.10.25/tools/aw_status_live.py"
dashmap = {'EU': '10.215.11.254',
	    'CA': '10.98.10.254',
	    'US': '10.102.11.254',
	    'US_IMP': '10.104.10.254'}

awlist = []
newcust_awlist = []

def top(vdc):
	TOP_HTML = """<HTML>
	<HEAD>
	<link href="http://10.63.10.25/ccd/ccd.css" rel="stylesheet" type="text/css">
	<title>Archive Writers Status in """+vdc+""" VDC</title>

	<style type="text/css">
	.open {border: solid 1px black;
		border-right: solid 1px;
		border-bottom: none;
		text-align: center;
		background:#FFFFFF;}

	.close {border: solid 1px black;
		border-right: solid 1px;
		text-align: center;
		background: #E0DFE3;}
	</style>

	</HEAD>

	<BODY BGCOLOR=#FFFFFF leftmargin=0 topmargin=0>
	<table border=0 width="90%" cellpadding=5 cellspacing=5>
	<tr>
	<td align=left valign="bottom">
	<table border=0 width="90%" cellpadding=5 cellspacing=5>
	<tr>
	<td valign="top" align="left">
	<img src="http://10.63.10.25/ccd/proofpoint_logo_17.gif" alt="Top left corner" border="0">
	</td>
	</tr>
	</table>
	</br>

	<table width="100%" border="0" cellpadding="5" cellspacing="5" style="PADDING-LEFT: 5px">

	<tr>
	<td align="left" colspan="3">
	<span class=maintitle><a href="""+base_url+""" style="text-decoration: none">Proofpoint Archiving - Archive Writers status</a></span><br></td>
	</tr>
	</table>"""

	print "Content-Type: text/html\n\n"
	print TOP_HTML

def nav_bar(vdc):

	stat = 'close'
	args = {'CA': stat, 'US': stat, 'EU': stat, 'US_IMP': stat, 'URL': base_url}
	args[vdc] = 'open'

	NAVBAR = """<table border=0 cellpadding=5 cellspacing=5" >
	<tr>
	<td class=%(CA)s><a href = %(URL)s?CA style="text-decoration: none">CA VDC</a></td>
	<td class=%(US)s><a href = %(URL)s?US style="text-decoration: none">US VDC</a></td>
	<td class=%(EU)s><a href = %(URL)s?EU style="text-decoration: none">EU VDC</a></td>
	<td class=%(US_IMP)s><a href = %(URL)s?US_IMP style="text-decoration: none">US IMPORT</a></td>
	</tr>"""

	print NAVBAR % args

def get_awlist(vdc):
	mysqlhost = dashmap[vdc]
	awlist = []
	query = "SELECT HostAddress FROM hosts WHERE HostTypeId = 5 AND HostActive = 1 order by INET_ATON(HostAddress);"
	try:
		db = MySQLdb.connect(host=mysqlhost,
		user="fortro",
		passwd="S-E-C-R-E-T",
		db="ops_dashboard")
	except MySQLdb.OperationalError:
		print "<span class=error>Error:  %s </span>" % sys.exc_info()[1]
		sys.exit()

	cursor = db.cursor()
	cursor.execute(query)
	rs = cursor.fetchall()
	for r in rs:
		awlist.append(r[0])

	return awlist

# function to get a list of AWs that
# can be used for new customers:
def get_newcust_awlist(vdc):
	mysqlhost = dashmap[vdc]
	newcust_awlist = []
	q = """SELECT host FROM aw_processing_times
		WHERE num_batches>0 AND
		date >= DATE_ADD(CURDATE(), INTERVAL -8 DAY) AND
		date <= CURDATE()
		GROUP BY host
		ORDER BY sum(num_batches),avg(total_time),avg(size_messages);"""
	try:
		db = MySQLdb.connect(host=mysqlhost,
							user="fortro",
							passwd="S-E-C-R-E-T",
							db="ops_dashboard")
	except MySQLdb.OperationalError:
		print "<span class=error>Error:  %s </span>" % sys.exc_info()[1]
		sys.exit()

	cursor = db.cursor()
	cursor.execute(q)
	rs = cursor.fetchall()
	for r in rs:
		newcust_awlist.append(r[0])

	return newcust_awlist


def startpage():
  print "This tool displays state of Archive Writers in the given Virtual Datacentre.<br>Please select from the list below:<br>"
  print "<table border=0 width=\"90%\" cellpadding=5 cellspacing=5>"
  print "<tr><td><a href = %s?CA style=\"text-decoration: none\">CA VDC</a></td></tr>" % base_url
  print "<tr><td><a href = %s?US style=\"text-decoration: none\">US VDC</a></td></td>" % base_url
  print "<tr><td><a href = %s?EU style=\"text-decoration: none\">EU VDC</a></td></tr>" % base_url
  print "<tr><td><a href = %s?US_IMP style=\"text-decoration: none\">US IMPORT</a></td></tr>" % base_url
  print "</table>"


def content(vdc):

	# get the list of AWs for the given VDC
	awlist = get_awlist(vdc)
	# pull a list of AWs, that could be used for creating new customers:
	newcust_awlist = get_newcust_awlist(vdc)

	print "<tr><td colspan=4>"
	print "<!-- nested table begins -->"
	print "<table border=0 cellpadding=5 cellspacing=0 >"
	print "<tr><td colspan=7><b>Archive Writers status in %s VDC</b></td></tr>" % vdc

	print """<tr class="cellheader" >
		<td class="cellheader rowcolor" ">AW</td>
		<td class="cellheader rowcolor">Total</td>
		<td class="cellheader rowcolor">Used</td>
		<td class="cellheader rowcolor">Available</td>
		<td class="cellheader rowcolor">Pct Used</td>
		<td class="cellheader rowcolor">Index Size</td>
		<td class="cellheader rowcolor">Structure Size</td>
		<td class="cellheader rowcolor">Queue</td>
		<td class="cellheader rowcolor align=left">Status</td>
		<td class="cellheader rowcolor">Start<br>Date</td>
		<td class="cellheader rowcolor">Capped<br>Date</td>
		<td class="cellheader rowcolor">Migrated<br>To</td>
		<td class="cellheader rowcolor">XML Logs<br>Server</td>
		<td class="cellheader rowcolor">Backups<br>Server</td>
		<td class="cellheader rowcolor">Replication Status</td>
		</tr>"""

	rowcount = 0
	for aw in awlist:
		#cmd = 'curl -sNf http://%s:8086/fortiva/AW.sh' % aw
		cmd = 'curl -sNf http://%s:8086/fortiva/ArchiveWriterStatus.pl?type=short' % aw
		out = os.popen(cmd).read().rstrip().split(':')

		if ( (rowcount % 2) == 1):
			rcolor = "rowcolor"
		else:
			rcolor = "rownocolor"
		rowcount = rowcount + 1

		# begin the row
		ROW = """<tr>
			<td class=\"%(RCOLOR)s\" >%(AW)s</td>
			<td class=\"%(RCOLOR)s\" >%(TOTAL)s</td>
			<td class=\"%(RCOLOR)s\" >%(USED)s</td>
			<td class=\"%(RCOLOR)s\" >%(AVAIL)s</td>
			<td class=\"%(RCOLOR)s\" >%(PCT)s</td>
			<td class=\"%(RCOLOR)s\" >%(INDX)s</td>
			<td class=\"%(RCOLOR)s\" >%(STRCT)s</td>"""

		f = []
   	   	for i in range(14):
   	   	 f.append("")
   	   	[ total, used, avail, pct, indx, strct, queue, writable, startdate, capdate,  migtarget, xmlmnt, bkmnt, repl ] = f

		if len(out) == 14:
			[ total, used, avail, pct, indx, strct ] = out[0:6]
			[ queue, writable ] = out[6:8]
			[ startdate, capdate ] = out[8:10]
			migtarget = out[10]
			xmlmnt = out[11]
			bkmnt = out[12]
			repl = out[13]

			# if the AW is in the list of potential new customer AWs and it's a legalhold AW - remove it
			# from the potential new customer AW list
			if aw in newcust_awlist:
				if not re.search("WRITABLE.+\(\s*([^a-zA-Z]+)\s*\)", writable):
					newcust_awlist.remove(aw)

			# continue the row here:
			print ROW % {'RCOLOR': rcolor, 'AW': aw, 'TOTAL': total, 'USED': used, 'AVAIL': avail, 'PCT': pct, 'INDX': indx, 'STRCT': strct}
			print "<td class=\"%s\" align=right><a href=\"http://%s:8086/fortiva/ArchiveWriterQueue.pl\" STYLE=\"TEXT-DECORATION: NONE\">%s</a></td>" %(rcolor, aw, queue)

			writable = writable.replace(' )',')')
			if re.search('WRITABLE', writable):
				print "<td class=\"%s\"><a href=\"http://%s:8086/fortiva/ArchiveWriterStatus.pl\" STYLE=\"TEXT-DECORATION: NONE\"><span style=\"color:red\">%s</span></a></td>" % (rcolor, aw, writable)
			elif re.search('READONLY', writable):
				print "<td class=\"%s\"><a href=\"http://%s:8086/fortiva/ArchiveWriterStatus.pl\" STYLE=\"TEXT-DECORATION: NONE\"><span style=\"color:blue\">%s</span></a></td>" % (rcolor, aw, writable)
			else:
				print "<td class=\"%s\"><span style=\"color:green\">%s</span></td>" % (rcolor, writable)

			print "<td class=\"%s \">%s</td>" % (rcolor, startdate)
			print "<td class=\"%s \">%s</td>" % (rcolor, capdate)
			print "<td class=\"%s \">%s</td>" % (rcolor, migtarget)
			print "<td class=\"%s \">%s</td>" % (rcolor, xmlmnt)
			print "<td class=\"%s \">%s</td>" % (rcolor, bkmnt)
			print "<td class=\"%s \">%s</td>" % (rcolor, repl)
			print "</tr>"

		else:
			print "<tr><td class=\"%s\" align=left>%s</td>" % (rcolor, aw)
			print "<td colspan=8 class=error align=center>Something's wrong with this one, please <a href=\"http://%s:8086/fortiva/ArchiveWriterStatus.pl?type=short\">check</a></td></tr>"	 % aw

	print "</td></tr></table>"
	print "<!-- end of nested table -->"
	print "</table>"

	print """<table border=0 cellpadding=5 cellspacing=5 style=\"PADDING-LEFT: 5px\" >
		<tr><td class="cellheader" colspan=3>AWs that can be used for new customers<br>
		(in this order of preference):</td></tr>"""
	print "<tr><td>"
	for a in newcust_awlist:
		print "%s<br>" %a
	print "</td></tr>"
	print "</table></body></html>"


def bottom(vdc):
	print """<table border=0 cellpadding=5 cellspacing=5 style=\"PADDING-LEFT: 5px\" >
    <tr><td class="cellheader" colspan=3>These are all Archive Writers in %s found in opsdashboard database.<br> If something's missed - talk to to Archiving Ops guys.</td></tr>
    </table></body></html>""" % vdc

def maintenance():
	print   """<table border=0 cellpadding=5 cellspacing=5 style=\"PADDING-LEFT: 5px\" >
    <tr><td class="cellheader" colspan=3>Maintenance. Come back later.<br>
    </td></tr> </table></body></html>"""

def master_control():
	if  os.environ["QUERY_STRING"] != '':

		vdc = os.environ["QUERY_STRING"]
		top(vdc)
		nav_bar(vdc)
		content(vdc)
		bottom(vdc)
	else:
		top('NONE')
		startpage()


master_control()
