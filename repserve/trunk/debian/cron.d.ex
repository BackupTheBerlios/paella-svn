#
# Regular cron jobs for the repserve package
#
0 4	* * *	root	[ -x /usr/bin/repserve_maintenance ] && /usr/bin/repserve_maintenance
