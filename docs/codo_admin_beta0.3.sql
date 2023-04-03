-- MySQL dump 10.14  Distrib 5.5.60-MariaDB, for Linux (x86_64)
--
-- Host: 127.0.0.1    Database: codo_admin
-- ------------------------------------------------------
-- Server version	5.7.26

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `mg_app_settings`
--

LOCK TABLES `mg_app_settings` WRITE;
/*!40000 ALTER TABLE `mg_app_settings` DISABLE KEYS */;
/*!40000 ALTER TABLE `mg_app_settings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `mg_components`
--

LOCK TABLES `mg_components` WRITE;
/*!40000 ALTER TABLE `mg_components` DISABLE KEYS */;
INSERT INTO `mg_components` VALUES (2,'edit_button','0'),(3,'publish_button','0'),(8,'reset_mfa_btn','0'),(9,'reset_pwd_btn','0'),(10,'new_user_btn','0'),(12,'get_token_btn','0'),(13,'web_ssh_btn','0'),(14,'asset_error_log','0');
/*!40000 ALTER TABLE `mg_components` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `mg_functions`
--

LOCK TABLES `mg_functions` WRITE;
/*!40000 ALTER TABLE `mg_functions` DISABLE KEYS */;
INSERT INTO `mg_functions` VALUES (6,'ss','/login/','ALL','10','2018-03-21 10:29:14','2018-03-20 18:35:24'),(9,'管理员','/','ALL','0','2018-03-21 14:04:59','2018-03-21 14:04:59'),(10,'任务管理员','/task/v2/task/','ALL','0','2019-03-21 10:57:54','2018-03-22 10:09:10'),(12,'修改密码','/mg/v2/accounts/password/','PATCH','0','2019-03-21 11:07:20','2018-03-22 16:27:12'),(15,'提交任务','/task/v2/task/accept/','POST','0','2019-03-21 10:57:29','2018-06-08 09:26:00'),(16,'获取CSRF','/task/v2/task/accept/','GET','0','2018-12-27 13:16:41','2018-06-08 09:26:51'),(33,'发布配置','/task/v2/task_other/publish_cd/','GET','0','2018-12-05 09:59:48','2018-12-05 09:37:24'),(35,'系统用户获取','/mg/v2/accounts/','GET','0','2018-12-14 14:44:51','2018-12-14 14:40:48'),(36,'发送邮件','/mg/v2/notifications/mail/','POST','0','2018-12-27 13:11:20','2018-12-27 13:11:20'),(37,'获取前端权限','/accounts/authorization/','GET','0','2018-12-27 16:28:07','2018-12-27 16:28:07'),(38,'获取镜像仓库信息','/task/v2/task_other/docker_registry/','GET','0','2019-01-14 16:12:58','2019-01-14 16:12:58'),(39,'已发布配置获取','/kerrigan/v1/conf/publish/','GET','0','2019-01-29 16:01:36','2019-01-29 16:01:36'),(40,'钩子提交任务','/task/v2/task/accept/','POST','0','2019-03-18 16:49:01','2019-03-18 16:48:48'),(42,'获取订单','/task/v2/task/list/','GET','0','2019-03-21 10:55:51','2019-03-21 10:55:51'),(43,'超管注册用户','/mg/register/','POST','0','2019-03-21 11:08:50','2019-03-21 11:05:28'),(44,'超管重置MFA','/mg/v2/accounts/reset_mfa/','PUT','0','2019-03-21 11:09:42','2019-03-21 11:09:42'),(45,'超管重置用户密码','/mg/v2/accounts/reset_pw/','PUT','0','2019-03-21 11:10:18','2019-03-21 11:10:18'),(46,'查看系统配置','/mg/v2/sysconfig/settings/','GET','0','2019-03-21 11:11:32','2019-03-21 11:11:32'),(47,'修改系统配置','/mg/v2/sysconfig/settings/','POST','0','2019-03-21 11:12:09','2019-03-21 11:12:09'),(48,'测试邮件和短信','/mg//v2/sysconfig/check/','POST','0','2019-03-21 11:12:40','2019-03-21 11:12:40'),(49,'用户管理所有权限','/mg//v2/accounts/','ALL','0','2019-03-21 11:13:43','2019-03-21 11:13:43'),(50,'发送短信API','/mg/v2/notifications/sms/','POST','0','2019-03-21 11:15:19','2019-03-21 11:15:19'),(51,'发送邮件API','/mg/v2/notifications/mail/','POST','0','2019-03-21 11:15:46','2019-03-21 11:15:46'),(52,'配置中心所有权限-项目要单独赋权','/kerrigan/v1/conf/','ALL','0','2019-03-21 11:40:13','2019-03-21 11:40:13'),(53,'调度任务日志','/task/ws/v1/task/log/','ALL','0','2019-04-12 09:22:39','2019-03-21 11:41:51'),(54,'查看任务详情','/task/v2/task/check/','GET','0','2019-03-21 11:47:15','2019-03-21 11:47:15'),(55,'查看历史任务','/task/v2/task/check_history/','GET','0','2019-03-21 12:09:43','2019-03-21 11:51:44'),(56,'干预调度任务','/task/v2/task/check/','PUT','0','2019-03-21 12:00:17','2019-03-21 11:54:50'),(57,'调度任务重做-终止','/task/v2/task/check/','PATCH','0','2019-04-25 18:00:54','2019-03-21 11:55:35'),(59,'调度任务模板','/task/v2/task_layout/','ALL','0','2019-03-21 11:57:36','2019-03-21 11:57:36'),(60,'调度任务全部终止','/task/v2/task/list/','PUT','0','2019-03-21 12:00:39','2019-03-21 12:00:39'),(61,'资产管理查看主机','/cmdb/v1/cmdb/server/','GET','0','2019-03-21 12:19:58','2019-03-21 12:05:00'),(62,'资产管理-查看主机组','/cmdb/v1/cmdb/server_group/','GET','0','2019-03-21 12:20:04','2019-03-21 12:05:18'),(63,'资产管理-查看审计日志','/cmdb/v1/cmdb/server_log/','GET','0','2019-03-21 12:20:08','2019-03-21 12:05:38'),(64,'数据库优化日志','/task/ws/v1/task/log_data/','ALL','0','2019-04-12 09:23:27','2019-04-12 09:23:27'),(65,'页面任务发布','/task//other/v1/submission/','ALL','0','2019-04-12 09:24:36','2019-04-12 09:24:36'),(66,'任务提交-发布','/task/other/v1/submission/publish/','ALL','0','2019-04-12 09:25:06','2019-04-12 09:25:06'),(67,'任务提交-数据库审计','/task/other/v1/submission/mysql_audit/','ALL','0','2019-04-12 09:25:55','2019-04-12 09:25:55'),(68,'任务提交-数据库优化','/task/other/v1/submission/mysql_opt/','ALL','0','2019-04-12 09:26:24','2019-04-12 09:26:24'),(69,'任务提交-自定义','/task/other/v1/submission/custom_task/','ALL','0','2019-04-12 09:26:54','2019-04-12 09:26:54'),(70,'任务提交-自定义-代理','/task/other/v1/submission/custom_task_proxy/','ALL','0','2019-04-12 09:27:49','2019-04-12 09:27:49'),(71,'任务提交-自定义-json','/task/other/v1/submission/post_task/','ALL','0','2019-04-12 09:28:18','2019-04-12 09:28:18'),(72,'获取有权限资产标签','/task/other/v1/record/tag_auth/','GET','0','2019-04-15 10:33:37','2019-04-15 10:33:37'),(73,'订单审批','/task/v2/task/list/','PATCH','0','2019-04-25 17:27:20','2019-04-25 17:27:20'),(74,'PrometheusWebHooks','/tools/v1/tools/send/prometheus/','POST','0','2019-04-26 17:30:10','2019-04-26 17:30:10'),(75,'任务统计','/task/v2/task/statement/','GET','0','2019-05-21 10:58:25','2019-05-21 10:58:25'),(76,'DNS页面所有权限','/dns/v1/dns/bind/','ALL','0','2019-05-23 09:17:17','2019-05-23 09:17:17'),(77,'DNS查看域名','/dns/v1/dns/bind/domain/','GET','0','2019-05-23 09:17:55','2019-05-23 09:17:55'),(78,'DNS添加域名','/dns/v1/dns/bind/domain/','POST','0','2019-05-23 09:18:20','2019-05-23 09:18:20'),(79,'DNS删除域名','/dns/v1/dns/bind/domain/','DELETE','0','2019-05-23 09:18:48','2019-05-23 09:18:48'),(80,'DNS域名禁用启用','/dns/v1/dns/bind/domain/','PATCH','0','2019-05-23 09:19:10','2019-05-23 09:19:10'),(81,'DNS-API脚本获取域名','/dns/v2/dns/bind/domain/','GET','0','2019-05-23 09:20:04','2019-05-23 09:20:04'),(82,'DNS-API脚本获取区域','/dns/v2/dns/bind/zone/','GET','0','2019-05-23 09:20:39','2019-05-23 09:20:39'),(83,'DNS-区域文件所有权限','/dns/v1/dns/bind/zone/','ALL','0','2019-05-23 09:21:23','2019-05-23 09:21:23'),(84,'DNS-添加解析','/dns/v1/dns/bind/zone/','POST','0','2019-05-23 09:21:58','2019-05-23 09:21:58'),(85,'DNS-查看解析','/dns/v1/dns/bind/zone/','GET','0','2019-05-23 09:22:39','2019-05-23 09:22:39'),(86,'DNS-删除解析','/dns/v1/dns/bind/zone/','DELETE','0','2019-05-23 09:23:02','2019-05-23 09:23:02'),(87,'DNS-修改解析','/dns/v1/dns/bind/zone/','PUT','0','2019-05-23 09:23:38','2019-05-23 09:23:38'),(88,'DNS-解析禁用启用','/dns/v1/dns/bind/zone/','PATCH','0','2019-05-23 09:24:09','2019-05-23 09:24:09'),(89,'DNS-获取配置','/dns/v1/dns/bind/conf/','GET','0','2019-05-23 09:24:57','2019-05-23 09:24:57'),(90,'DNS-查看日志','/dns/v1/dns/bind/log/','GET','0','2019-05-23 09:25:31','2019-05-23 09:25:31'),(91,'CMDB-获取主机','/cmdb2//v1/cmdb/server/','GET','0','2019-05-23 10:02:48','2019-05-23 10:02:48'),(92,'CMDB-添加主机','/cmdb2/v1/cmdb/server/','POST','0','2019-05-23 10:16:29','2019-05-23 10:16:29'),(93,'CMDB-更新主机','/cmdb2/v1/cmdb/server/','PUT','0','2019-05-23 10:16:57','2019-05-23 10:16:57'),(94,'CMDB-删除主机','/cmdb2/v1/cmdb/server/','DELETE','0','2019-05-23 10:17:18','2019-05-23 10:17:18'),(95,'CMDB-查看主机详情','/cmdb2/v1/cmdb/server_detail/','GET','0','2019-05-23 10:22:24','2019-05-23 10:22:24'),(96,'CMDB-获取DB','/cmdb2/v1/cmdb/db/','GET','0','2019-05-23 10:24:11','2019-05-23 10:24:11'),(97,'CMDB-添加DB','/cmdb2/v1/cmdb/db/','POST','0','2019-05-23 10:24:22','2019-05-23 10:24:22'),(98,'CMDB-更新DB','/cmdb2/v1/cmdb/db/','PUT','0','2019-05-23 10:24:46','2019-05-23 10:24:46'),(99,'CMDB-删除DB','/cmdb2/v1/cmdb/db/','DELETE','0','2019-05-23 10:25:02','2019-05-23 10:25:02'),(100,'CMDB-获取标签','/cmdb2/v1/cmdb/tag/','GET','0','2019-05-23 10:25:46','2019-05-23 10:25:46'),(101,'CMDB-添加标签','/cmdb2/v1/cmdb/tag/','POST','0','2019-05-23 10:26:21','2019-05-23 10:26:15'),(102,'CMDB-更新标签','/cmdb2/v1/cmdb/tag/','PUT','0','2019-05-23 10:26:42','2019-05-23 10:26:42'),(103,'CMDB-删除标签','/cmdb2/v1/cmdb/tag/','DELETE','0','2019-05-23 10:26:54','2019-05-23 10:26:54'),(104,'CMDB-主机资产更新','/cmdb2//v1/cmdb/server/asset_update/','POST','0','2019-05-23 10:27:35','2019-05-23 10:27:35'),(105,'CMDB-获取资产配置','/cmdb2/v1/cmdb/asset_configs/','GET','0','2019-05-23 10:28:14','2019-05-23 10:28:14'),(106,'CMDB-添加资产配置','/cmdb2/v1/cmdb/asset_configs/','POST','0','2019-05-23 10:28:27','2019-05-23 10:28:27'),(107,'CMDB-更新资产配置','/cmdb2/v1/cmdb/asset_configs/','PUT','0','2019-05-23 10:28:39','2019-05-23 10:28:39'),(108,'CMDB-删除资产配置','/cmdb2/v1/cmdb/asset_configs/','DELETE','0','2019-05-23 10:28:56','2019-05-23 10:28:56'),(109,'CMDB-拉取云厂商主机信息','/cmdb2//v1/cmdb/asset_configs/handler_update_server/','GET','0','2019-05-23 11:02:32','2019-05-23 11:02:32');
/*!40000 ALTER TABLE `mg_functions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `mg_menus`
--

LOCK TABLES `mg_menus` WRITE;
/*!40000 ALTER TABLE `mg_menus` DISABLE KEYS */;
INSERT INTO `mg_menus` VALUES (1,'home','0'),(2,'_home','0'),(3,'components','0'),(4,'count_to_page','0'),(5,'tables_page','0'),(6,'usermanage','0'),(7,'user','0'),(8,'role','0'),(9,'functions','0'),(10,'menus','0'),(12,'systemmanage','0'),(13,'system','0'),(14,'systemlog','0'),(18,'cron','0'),(19,'cronjobs','0'),(20,'cronlogs','0'),(22,'task_layout','0'),(23,'commandlist','0'),(24,'argslist','0'),(25,'templist','0'),(26,'order','0'),(27,'taskOrderList','0'),(28,'taskuser','0'),(29,'operation_center','0'),(32,'mysqlAudit','0'),(33,'publishApp','0'),(34,'mysqlOptimize','0'),(35,'resourceApplication','0'),(37,'customTasks','0'),(38,'publishConfig','0'),(39,'codeRepository','0'),(40,'dockerRegistry','0'),(41,'cmdb','0'),(42,'asset_server','0'),(43,'log_audit','0'),(46,'tag_mg','0'),(47,'admin_user','0'),(50,'k8s','20'),(51,'project','20'),(52,'app','20'),(53,'project_publish','0'),(54,'publish_list','0'),(55,'statisticaldata','0'),(56,'statisticalImage','0'),(57,'historyTaskList','0'),(58,'asset_db','0'),(59,'config_center','0'),(60,'project_config_list','0'),(61,'my_config_list','0'),(62,'confd','0'),(63,'confd_project','0'),(64,'confd_config','0'),(65,'devopstools','0'),(66,'prometheus_alert','0'),(68,'tagTree','0'),(69,'event_manager','0'),(70,'password_mycrypy','0'),(72,'proxyInfo','0'),(73,'paid_reminder','0'),(74,'project_manager','0'),(75,'postTasks','0'),(76,'taskCenter','0'),(77,'fault_manager','0'),(78,'assetPurchase','0'),(79,'nodeAdd','0'),(80,'customTasksProxy','0'),(85,'web_ssh','0'),(87,'tag_mg','0'),(88,'assetPurchaseALY','0'),(89,'assetPurchaseAWS','0'),(90,'assetPurchaseQcloud','0'),(91,'domain','0'),(92,'domain_name_manage','0'),(93,'domain_name_monitor','0'),(94,'system_user','0'),(95,'asset_config','0');
/*!40000 ALTER TABLE `mg_menus` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `mg_role_functions`
--

LOCK TABLES `mg_role_functions` WRITE;
/*!40000 ALTER TABLE `mg_role_functions` DISABLE KEYS */;
/*!40000 ALTER TABLE `mg_role_functions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `mg_role_menus`
--

LOCK TABLES `mg_role_menus` WRITE;
/*!40000 ALTER TABLE `mg_role_menus` DISABLE KEYS */;
/*!40000 ALTER TABLE `mg_role_menus` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `mg_roles`
--

LOCK TABLES `mg_roles` WRITE;
/*!40000 ALTER TABLE `mg_roles` DISABLE KEYS */;
/*!40000 ALTER TABLE `mg_roles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `mg_roles_components`
--

LOCK TABLES `mg_roles_components` WRITE;
/*!40000 ALTER TABLE `mg_roles_components` DISABLE KEYS */;
/*!40000 ALTER TABLE `mg_roles_components` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `mg_user_roles`
--

LOCK TABLES `mg_user_roles` WRITE;
/*!40000 ALTER TABLE `mg_user_roles` DISABLE KEYS */;
/*!40000 ALTER TABLE `mg_user_roles` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `mg_users`
--

LOCK TABLES `mg_users` WRITE;
/*!40000 ALTER TABLE `mg_users` DISABLE KEYS */;
INSERT INTO `mg_users` VALUES (1,'admin','66e7bcb387a66f2bf98ad62de7b8a82c','admin','191715030@qq.com','11111111111','','','admin','','0','0','180.168.11.84','2019-05-24 10:39:29','2017-12-21 14:26:04');
/*!40000 ALTER TABLE `mg_users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `operation_record`
--

LOCK TABLES `operation_record` WRITE;
/*!40000 ALTER TABLE `operation_record` DISABLE KEYS */;
/*!40000 ALTER TABLE `operation_record` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2019-05-24 10:39:42
