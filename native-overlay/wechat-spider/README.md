# 拾万句 APP · 历史文章采集测试

此页面调用 [lqqyt2423/wechat_spider](https://github.com/lqqyt2423/wechat_spider) 已提供的 REST API，展示它实际采集并写入 MongoDB 的公众号历史文章。APP 本身不伪装成爬虫，也不会绕过微信登录或证书机制。

## 1. 在电脑或服务器运行采集服务

按照上游仓库 README 安装 Node.js 16、MongoDB 和 Redis：

```bash
git clone https://github.com/lqqyt2423/wechat_spider.git
cd wechat_spider
npm install
npm start
```

默认服务端口：
- HTTP API / 数据管理页面：8104
- AnyProxy HTTP/HTTPS 代理：8101
- AnyProxy 管理页面（开发环境）：8102

也可以使用上游仓库提供的 Docker Compose 部署方式。MongoDB 数据库名为 `wechat_spider`，文章和公众号分别保存在 `posts`、`profiles` 集合。

## 2. 首次采集「拾万句」

1. 让手机和运行采集服务的电脑连接同一个 Wi-Fi。
2. 在手机 Wi-Fi 代理设置中填写电脑的局域网 IP，端口填写 `8101`。
3. 按 AnyProxy 官方说明安装并信任 HTTPS 根证书。只在你信任的设备和网络环境中安装自己的代理证书。
4. 保持微信登录，在微信中搜索「拾万句」，进入公众号主页并打开「全部消息 / 历史消息」页面。
5. 观察电脑运行日志，并在服务端管理页面 `http://电脑IP:8104` 确认公众号和文章已写入数据库。
6. 回到拾万句 APP「我的 → 历史文章」，设置服务地址，例如 `http://192.168.1.20:8104`，点击「连接并读取」。

首次打开历史页时，页面可能需要滚动或等待自动翻页脚本执行，采集结果不是瞬间完成的。采集到的文章会逐步显示在 APP 页面中。

## 3. APP 使用的上游接口

- `GET /api/profiles?page=1&perPage=100`：读取已采集公众号及其 `msgBiz`、头像、名称。
- `GET /api/posts?msgBiz={msgBiz}&sortWay=-publishAt&page={page}&perPage=20`：分页读取历史文章。
- `GET /api/posts/{id}`：读取文章详情中的封面和摘要。上游列表接口当前不返回这两个字段，因此 APP 对每篇列表文章补充读取详情。

## 4. 注意事项

- 这是代理采集架构，不是 APP 内置的无登录云端爬虫。必须先运行独立采集服务并让微信流量经过代理。
- 如果手机无法访问电脑的 `8104` 端口，请检查同一局域网、电脑防火墙和服务监听状态。
- HTTP 局域网连接仅用于测试。若部署到公网，请使用 HTTPS、访问控制和防火墙，不要把未保护的管理页面直接暴露到公网。
- 微信页面结构、访问频率限制和账号权限可能影响抓取完整度；不能保证每个账号都能一次性获取全部历史文章。
- 上游项目采用 MIT License。采集服务部署时请保留上游项目的版权及许可声明，并遵守微信平台规则及内容使用权限。
