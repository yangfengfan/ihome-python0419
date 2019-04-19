echo !!!!!!!!Attention!!!!!!!!!! please excute this command in Console, not ssh or other place
cd /ihome

rm -rf settings
rm -rf .project
rm -rf .pydevproject


#/ihome/setapssid.sh

echo "Begin to Get IP address"
cnt=0
while (test $cnt != 20)
do
	if ifconfig eth0 | grep "inet addr" > /dev/null; then
	        break
        fi
	cnt=`expr $cnt + 1`
        if [ $cnt -eq 5 ]; then
        	ifconfig eth0 down
        	sleep 1
		ifconfig eth0 up
		sleep 5
	fi
        if [ $cnt -eq 10 ]; then
        	ifconfig eth0 down
        	sleep 1
		ifconfig eth0 up
		sleep 5
	fi
	echo ")))))))))))))))))))))))))))))))$cnt(((((((((((((((((((((("
	sleep 2     
done

if [ $cnt = 20 ]; then
	echo "Get IP address failed"
	exit 0
else
	echo "Get IP address successed"
fi 

echo start smart_home
killall smart_home
/smart_home/smart_home &

#echo start redis-server
#killall redis
#cd /ihome/redis/bin
#./redis-server redis.conf &

killall python
echo start scanservice
cd /ihome/main
python /ihome/main/ScanService.pyc &

killall httpd
echo start webserver at port 8080
cd /ihome/main
python /ihome/main/webpy.pyc 8080 &

echo start main
cd /ihome/main
python /ihome/main/main.pyc &
