# 拾万句 APP · wechat_spider 历史文章采集服务

本目录提供对 [lqqyt2423/wechat_spider](https://github.com/lqqyt2423/wechat_spider) 的 Docker 部署入口。采集引擎仍由上游项目执行；拾万句 APP 的「历史文章」页面通过上游的 `/api/profiles`、`/api/posts` 接口读取已采集数据。

## 重要说明

- 该爬虫不是仅凭公众号名称即可在后台自动抓取的服务。它依赖手机微信经过 AnyProxy 代理打开公众号历史页，才能捕获历史文章及账号标识。
- 首次采集需要手机和运行 Docker 的电脑处于同一局域网；手机代理地址设为电脑局域网 IP，端口为 `8101`。
- HTTPS 代理需要在手机上安装本次容器生成的根证书。不要使用上游仓库公开的旧私钥；本部署镜像会删除上游证书目录，由 AnyProxy 在首次启动时生成独立证书。
- 上游服务的 `8104` API 没有登录认证。只在可信局域网使用，不要直接映射到公网或配置公网端口转发。
- 微信客户端版本、系统证书策略及微信自身的 HTTPS 校验可能影响捕获效果；本集成不保证每个账号都能完整翻页。

## 启动采集服务

在仓库根目录执行：

```bash
docker compose -f wechat-spider-integration/docker-compose.yml up -d --build
```

查看日志，确认出现 AnyProxy 代理地址及数据管理页面地址：

```bash
docker compose -f wechat-spider-integration/docker-compose.yml logs -f app
```

电脑局域网 IP 假设为 `192.168.1.20`，则：
- 代理地址：`192.168.1.20:8101`
- API 地址：`http://192.168.1.20:8104`
- 上游数据管理页面：`http://192.168.1.20:8104`

将容器生成的证书复制出来：

```bash
docker compose -f wechat-spider-integration/docker-compose.yml cp app:/root/.anyproxy/certificates/rootCA.crt ./wechat-spider-rootCA.crt
```

把 `wechat-spider-rootCA.crt` 安装到测试手机的用户证书/CA 证书存储中。不同 Android 版本的菜单名称可能不同。仅在你控制的测试设备和网络中安装；测试结束后可移除该用户证书。

## 首次采集流程

1. 手机与 Docker 主机连接同一 Wi-Fi。
2. 在手机 Wi-Fi 的代理设置中选择手动代理，主机填写电脑局域网 IP，端口填写 `8101`。
3. 在手机微信中打开目标公众号的历史文章页面；如果从 APP 的「历史文章」页点击“在微信中打开历史页”，需要先在页面设置中填入该公众号的 `msgBiz`。
4. 在微信历史文章列表中向下滚动，等待上游爬虫自动翻页并捕获请求。上游默认的自动翻页规则和时间范围可在容器内的 `config.js` 调整。
5. 打开 `http://电脑局域网IP:8104`，确认上游管理界面出现公众号及文章记录。
6. 在拾万句 APP「我的 → 历史文章 → 设置」填写 API 地址 `http://电脑局域网IP:8104`，连接后选择已采集公众号；也可手动填写 `msgBiz`。
7. 页面会通过 `/api/posts?msgBiz=...` 分页读取采集结果，点文章卡片可在微信中打开原文。

## 停止服务

```bash
docker compose -f wechat-spider-integration/docker-compose.yml down
```

数据库和 CA 证书保存在 Docker named volumes 中。不要使用 `down -v`，除非确认要删除采集数据和证书。

## 上游项目

- 源码：<https://github.com/lqqyt2423/wechat_spider>
- License：MIT（上游项目的版权及许可文件随容器内源码保留）
