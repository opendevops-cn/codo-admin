#!/bin/bash -x

sleep 1

token="e09d6153f1c15395144794GtmAhRT4"
mg_addr="172.22.0.7:8000"

# 函数：发送 HTTP 请求
send_request() {
  curl "http://127.0.0.1:8888$1" -H "X-Api-Token: ${token}" -X POST -d "$2"
}

# 配置路由
send_request "/api/admin/routes/save" '{
    "key": "/api/mg/*",
    "protocol": "http",
    "remark": "",
    "prefix": "/api/mg/*",
    "service_name": "mg",
    "status": 1,
    "plugins": [
        "discovery",
        "tracing",
        "rewrite"
    ],
    "props": {
        "rewrite_url_regex": "^/api/mg/",
        "rewrite_replace": "/"
    }
}'

send_request "/api/admin/routes/save" '{
    "key": "/api/acc/*",
    "protocol": "http",
    "remark": "",
    "prefix": "/api/acc/*",
    "service_name": "mg",
    "status": 1,
	  "plugins": ["rewrite","discovery","tracing"],
    "props": {
      "rewrite_url_regex": "^/api/acc",
      "rewrite_replace": "/v4/na"
    }
}'

send_request "/api/admin/routes/save" '{
    "key": "/api/p/*",
    "protocol": "http",
    "remark": "",
    "prefix": "/api/p/*",
    "service_name": "mg",
    "status": 1,
	  "plugins":["rewrite","discovery"],
    "props": {
        "rewrite_url_regex": "^/api/p/",
        "rewrite_replace": "/"
    }
}'

send_request "/api/admin/routes/save" '{
    "key": "/api/agent/*",
    "protocol": "http",
    "remark": "",
    "prefix": "/api/agent/*",
    "service_name": "agent",
    "status": 1,
	"plugins": ["rewrite","tracing","discovery"],
    "props": {}
}'

send_request "/api/admin/routes/save" '{
    "key": "/api/cmdb/*",
    "protocol": "http",
    "remark": "cmdb",
    "prefix": "/api/cmdb/*",
    "service_name": "cmdb",
    "status": 1,
	"plugins":["rewrite","tracing","discovery","redis-logger"],
    "props": {}
}'

send_request "/api/admin/routes/save" '{
    "key": "/api/job/*",
    "protocol": "http",
    "remark": "job",
    "prefix": "/api/job/*",
    "service_name": "job",
    "status": 1,
	"plugins":["rewrite","tracing","discovery"],
    "props": {"rewrite_url_regex":"^\/api\/job\/","rewrite_replace":"\/"}
}'

send_request "/api/admin/routes/save" '{
    "key": "/api/kerrigan/*",
    "protocol": "http",
    "remark": "kerrigan",
    "prefix": "/api/kerrigan/*",
    "service_name": "kerrigan",
    "status": 1,
	"plugins":["rewrite","mjwt","discovery"],
    "props": {"rewrite_url_regex":"^\/api\/kerrigan\/","rewrite_replace":"\/"}
}'

send_request "/api/admin/routes/save" '{
    "key": "/api/noc/*",
    "protocol": "http",
    "remark": "通知",
    "prefix": "/api/noc/*",
    "service_name": "noc",
    "status": 1,
	"plugins":["rewrite","discovery"],
    "props": {"rewrite_url_regex":"^\/api\/noc\/","rewrite_replace":"\/"}
}'

send_request "/api/admin/routes/save" '{
    "key": "/api/v2/cmdb/*",
    "protocol": "http",
    "remark": "cmdb",
    "prefix": "/api/v2/cmdb/*",
    "service_name": "cmdb",
    "status": 1,
	"plugins":["mjwt","discovery","rewrite"],
    "props": {"rewrite_url_regex":"^\/api\/cmdb\/","rewrite_replace":"\/"}
}'

send_request "/api/admin/routes/save" '{
    "key": "/api/accounts/authorization/",
    "protocol": "http",
    "remark": "鉴权",
    "prefix": "/api/accounts/authorization/",
    "service_name": "mg",
    "status": 1,
    "plugins": [
        "discovery",
        "tracing",
        "limit-req",
        "rewrite"
    ],
    "props": {
      "limit_req_rate": 5,
      "rewrite_replace": "/",
      "rewrite_url_regex": "^/api/",
      "limit_req_burst": 5
    }
}'

send_request "/api/admin/routes/save" '{
    "key": "/api/accounts/login/",
    "protocol": "http",
    "remark": "登录",
    "prefix": "/api/accounts/login/",
    "service_name": "mg",
    "status": 1,
    "plugins": [
        "discovery",
        "tracing",
        "limit-req",
        "rewrite"
    ],
    "props": {
      "limit_req_rate": 5,
      "rewrite_replace": "/",
      "rewrite_url_regex": "^/api/",
      "limit_req_burst": 5
    }
}'

# 配置服务
send_request "/api/admin/services/save" '{
    "key": "/mg/172.22.0.7:8000",
    "service_name": "mg",
    "upstream": "172.22.0.7:8000",
    "weight": 1,
    "status": 1
}'
send_request "/api/admin/services/save" '{
    "key": "/p/172.22.0.7:8000",
    "service_name": "p",
   "upstream": "172.22.0.7:8000",
    "weight": 1,
    "status": 1
}'

#send_request "/api/admin/services/save" '{
#    "key": "/agent/${mg_addr}",
#    "service_name": "agent",
#    "upstream": "${mg_addr}",
#    "weight": 1,
#    "status": 1
#}'
#send_request "/api/admin/services/save" '{
#    "key": "/cmdb/${mg_addr}",
#    "service_name": "cmdb",
#    "upstream": "${mg_addr}",
#    "weight": 1,
#    "status": 1
#}'
#send_request "/api/admin/services/save" '{
#    "key": "/cron/${mg_addr}",
#    "service_name": "cron",
#    "upstream": "${mg_addr}",
#    "weight": 1,
#    "status": 1
#}'
#send_request "/api/admin/services/save" '{
#    "key": "/job/${mg_addr}",
#    "service_name": "job",
#    "upstream": "${mg_addr}",
#    "weight": 1,
#    "status": 1
#}'
#send_request "/api/admin/services/save" '{
#    "key": "/kerrigan/${mg_addr}",
#    "service_name": "kerrigan",
#    "upstream": "${mg_addr}",
#    "weight": 1,
#    "status": 1
#}'

exit 0
