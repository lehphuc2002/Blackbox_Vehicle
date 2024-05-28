#!/bin/sh
#stops the raspivid process
pid=`pidof raspivid`
`kill -2 $pid`