# 飞书配置步骤
## 1 登陆飞书开放平台
访问网址[https://open.feishu.cn/?lang=zh-CN](https://open.feishu.cn/?lang=zh-CN)，点击右上角的开发者后台。
![飞书开发者平台](../pics/feishu1.png)
如果没有组织，请先按照提示注册组织。完成后再执行后续步骤。
## 2 创建企业自建应用
![](../pics/feishu2.png)
## 3 添加机器人能力
![](../pics/feishu3.png)
## 4 开通收发消息权限
![](../pics/feishu4.png)
![](../pics/feishu5.png)
![](../pics/feishu6.png)
![](../pics/feishu7.png)
## 5 设置事件与回调
![](../pics/feishu8.png)
![](../pics/feishu15.png)
![](../pics/feishu9.png)
## 6 获取并记录APP ID和APP Secret
![](../pics/feishu10.png)
将这两个信息记录，填写到EasyGS配置文件中
```
~/.easygs/config.yaml
```
![](../pics/feishu11.png)
## 7 发布应用
![](../pics/feishu12.png)
![](../pics/feishu13.png)
## 8 开始使用
先执行网关启动命令
```
easygs gateway
```
然后点击打开应用，开始基因组育种分析流程。
![](../pics/feishu14.png)
