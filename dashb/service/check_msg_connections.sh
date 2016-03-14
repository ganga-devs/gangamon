#!/bin/bash

#calculate the number of ActiveMQ servers behind the DNS alias
let p=`host dashb-mb.cern.ch | wc -l`
#we should have 4 ports open to each ActiveMQ server
let 'expected = p*4'


#check that we still have $expected established TCP connections to the ActiveMQ servers on port 6162


est_conn=`/bin/netstat -ant | /usr/bin/awk '{print $5}' | grep 61123 | wc -l`

if [ $est_conn -eq $expected ]
   then
	exit 0
   else
	exit 1
fi

