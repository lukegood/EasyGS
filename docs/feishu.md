# Feishu Setup Guide

## 1. Log In to the Feishu Open Platform

Visit [https://open.feishu.cn/?lang=en-US](https://open.feishu.cn/?lang=en-US) and click **Developer Console** in the upper-right corner.

![Feishu developer platform](../pics/feishu1.png)

If you do not have an organization yet, please register one first and then continue with the following steps.

## 2. Create an In-House Enterprise App

![](../pics/feishu2.png)

## 3. Add the Bot Capability

![](../pics/feishu3.png)

## 4. Enable Message Send and Receive Permissions

![](../pics/feishu4.png)
![](../pics/feishu5.png)
![](../pics/feishu6.png)
![](../pics/feishu7.png)

## 5. Configure Events and Callbacks

![](../pics/feishu8.png)
![](../pics/feishu15.png)
![](../pics/feishu9.png)

## 6. Get and Record the App ID and App Secret

![](../pics/feishu10.png)

Record these two values and fill them into the EasyGS configuration file:

```text
~/.easygs/config.json
```

![](../pics/feishu11.png)

## 7. Publish the App

![](../pics/feishu12.png)
![](../pics/feishu13.png)

## 8. Start Using It

First, start the gateway service:

```bash
easygs gateway
```

Then open the app and begin your genomic breeding analysis workflow.

![](../pics/feishu14.png)
