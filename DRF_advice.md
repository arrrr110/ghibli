## 全页面接口使用总览

| 页面 | 主接口 | 辅助接口 | 评级 |
|------|--------|---------|------|
| `HomePage` | `getTopics`（游标分页） | `markTopicRead` / `likeTopic` / `subscribeTopic` / `addComment` | ✅ 合理 |
| `CreateTopicPage` | `createDraft` 或 `getTopic`（编辑） | `uploadTopicImage` / `deleteTopicImage` / `publishTopic` / `updateTopic` / `deleteTopic` | ⚠️ 草稿机制偏重 |
| `SubscriptionsPage` | `getTopics({page_size:50})` | `subscribeTopic` / `deleteTopic` | ❌ **前端过滤耦合** |
| `ProfilePage` | `getTopics({page_size:50})` | `updateProfile` | ❌ **用列表接口做统计** |
| `InvitePage` | `getInvitations` | 无 | ✅ 合理 |
| `TopicDetailPage` | `getTopic(id)`（含嵌套评论） | `likeTopic` / `subscribeTopic` / `addComment` / `deleteTopicImage` / `pinTopic` / `hideTopic` / `closeTopic` | ✅ 合理 |
| `MembersPage` | `getCommunityMembers`（调两次） | `verifyMember` / `kickMember` / `unverifyMember` | ⚠️ 同接口双调 |
| `TopicManagementPage` | `getTopics({status})` | `pinTopic` / `closeTopic` / `hideTopic` | ✅ 合理 |
| `AuthPage` | `login` | `sendCode` | ✅ 合理 |
| `WaitingVerificationPage` | `refreshUser`（轮询） | `getUserProfile` / `getCommunities` / `getCommunities({mine})` / `switchCommunity` | ⚠️ 页面职责过载 |
| `CreateCommunityPage` | `createCommunity` | 无 | ✅ 合理 |
| `UpdateAvatarPage` | `uploadAvatar` | `refreshUser` | ✅ 合理 |

---

## ❌ 严重问题（建议后端改）

### 问题 1：`ProfilePage` 用话题列表接口做统计 —— 严重耦合

**现状**：个人中心页需要 4 个统计数字（发起话题数、订阅数、支持数、已读数），但调用的是 `getTopics({ page_size: 50 })`，拉 50 条完整话题数据（含 `hot_comments`、`images` 等重字段）后在前端 `filter + length` 计数。

**问题**：
- **用错了接口**：话题列表接口不是为统计设计的，返回的是完整话题对象，数据量极大
- **数据不准**：只拉 50 条，超出部分统计不到，用户话题多了数字就是错的
- **性能浪费**：为了 4 个数字传输 50 条完整话题 JSON

**给后端的建议**：

> 新增 `GET /api/neighbor-hub/users/me/stats/` 接口，直接返回聚合统计

```json
{
  "topics_count": 12,
  "subscriptions_count": 5,
  "liked_count": 8,
  "read_count": 30
}
```

一条 SQL `COUNT + GROUP BY` 就能搞定，比返回 50 条完整话题对象高效得多。个人中心页的主接口就变成这个统计接口，`updateProfile` 作为辅助接口，完美符合「一主 + 若干辅」。

---

### 问题 2：`SubscriptionsPage` 没用专用筛选 —— 前端过滤耦合

**现状**：订阅记录页有「我的订阅」和「我的话题」两个 Tab，但只调了一次 `getTopics({ page_size: 50 })` 拉全量话题，然后在前端：
- 订阅列表 = `allTopics.filter(t => t.is_subscribed)`
- 我的话题 = `allTopics.filter(t => t.author === user?.user_id)`

**问题**：
- **后端已有能力但没用**：`getTopics` 已支持 `filter=subscribed`，但前端没传
- **缺少 `filter=mine`**：后端 `filter` 参数支持 `all / unread / read / liked / subscribed`，**唯独没有 `mine`（我的话题）**，所以「我的话题」Tab 只能前端过滤
- **全量拉取风险**：50 条不够就漏数据，拉太多又浪费

**给后端的建议**：

> 1. `getTopics` 的 `filter` 参数新增 `mine` 取值，筛选 `author = 当前用户` 的话题
> 2. 确保 `filter=subscribed` 返回的数据只包含已订阅话题（而非全量带 `is_subscribed` 标记）

改完后，订阅页两个 Tab 分别用 `getTopics({ filter: 'subscribed' })` 和 `getTopics({ filter: 'mine' })` 作为各自的主接口，干净利落。

---

## ⚠️ 中等问题（建议优化）

### 问题 3：`getTopics` 接口被 4 个页面复用，承担职责过多

**现状**：`getTopics` 一个接口被 HomePage、SubscriptionsPage、ProfilePage、TopicManagementPage 四个页面调用，每个传不同参数组合：

| 页面 | 参数 | 实际用途 |
|------|------|---------|
| HomePage | `{page_size: 20}` | 卡片浏览，后端默认排除已读未订阅 |
| SubscriptionsPage | `{page_size: 50}` | 拉全量前端过滤（应改用 `filter`） |
| ProfilePage | `{page_size: 50}` | 拉全量做统计（应改用 stats 接口） |
| TopicManagementPage | `{status, page_size: 20}` | 按状态筛选管理 |

**评价**：HomePage 和 TopicManagementPage 的用法是对的，参数语义清晰。但 SubscriptionsPage 和 ProfilePage 是明显的误用——一个拿列表接口做过滤，一个拿列表接口做统计。改掉这两处后，`getTopics` 的职责就回归正常了。

---

### 问题 4：`CreateTopicPage` 草稿机制 —— 轻度过度设计

**现状**：创建话题需要 3 个接口配合：`createDraft()` → `uploadTopicImage()` → `publishTopic()`，离开时还要 `deleteTopic()` 清理草稿。

**评价**：对于原型应用来说草稿机制偏重，但有其合理性——图片上传需要 `topic_id` 作为挂载点，不用草稿就得前端先存 base64 再一次性提交。**如果后端支持话题+图片一步创建就不需要草稿了**，但当前设计可接受，不建议改。

---

### 问题 5：`WaitingVerificationPage` 页面职责过载 —— 5 种接口

**现状**：一个页面同时承担三种职责，调了 5 种接口：
- 等待审核轮询：`refreshUser()`（即 `getMyProfile`，每 5 秒轮询）
- 邀请人信息：`getUserProfile(invitedBy)`
- 选择小区：`getCommunities()` + `switchCommunity()`
- 查看创建申请：`getCommunities({ mine: true })`

**评价**：这是前端页面拆分问题（应该拆成「选择小区」和「等待审核」两个独立页面），不完全是后端的问题。但后端可以考虑：

> `getMyProfile` 的返回值中已包含 `is_verified` / `community` / `community_name`，轮询用这个接口判断认证状态是合理的。但 `getCommunities({ mine: true })` 在轮询中也被重复调用（每次 5 秒），建议后端在 `getMyProfile` 返回值中附带 `my_communities` 字段，减少一个独立请求。

---

### 问题 6：`MembersPage` 同接口双调

**现状**：「待审核」和「正式成员」两个 Tab 分别调 `getCommunityMembers(id, { is_verified: false })` 和 `getCommunityMembers(id, { is_verified: true })`，切换 Tab 重新请求。

**评价**：两个 Tab 数据量通常都不大，可以考虑一次请求不带 filter 拿全量前端分组。但当前做法也不算错——各自独立分页、独立刷新。**低优先级，可不改。**

---

## ✅ 设计良好的部分

1. **`TopicDetailPage`**：主接口 `getTopic(id)` 返回的话题详情直接嵌套了 `comments` 数组，不需要再调 `getComments` 二次请求。前端 API 层虽然定义了 `getComments`，但页面没误用，很好。

2. **`HomePage`**：游标分页 + 交互操作（点赞/订阅/已读/留言）作为辅助接口，职责清晰。自动加载下一页的阈值控制也合理。

3. **`TopicManagementPage`**：按 `status` 筛选话题列表 + 三个管理操作（置顶/关闭/隐藏），符合「一主 + 若干辅」。

4. **`InvitePage`**：邀请码/链接从前端用户信息生成，只调一个 `getInvitations` 拉记录，无多余请求。

---

## 给后端的改进清单（按优先级）

| 优先级 | 改进项 | 涉及接口 |
|--------|--------|---------|
| **P0** | 新增用户统计接口 `GET /users/me/stats/`，返回 `{topics_count, subscriptions_count, liked_count, read_count}` | 新增 |
| **P0** | `getTopics` 的 `filter` 参数新增 `mine` 取值（筛选当前用户发起的话题） | `GET /topics/` |
| **P1** | `getMyProfile` 返回值附带 `my_communities`（我创建的小区列表），减少 WaitingVerificationPage 的额外请求 | `GET /users/me/` |
| **P2** | `getCommunityMembers` 支持一次性返回全量成员（不带 filter），前端按 `is_verified` 分组 | `GET /communities/{id}/members/` |

P0 两项改完后，`ProfilePage` 和 `SubscriptionsPage` 的耦合问题就能彻底解决，全站接口使用都会符合「一主 + 若干辅」原则。

以上就是全站 12 个页面的接口使用审查和给后端的改进建议。核心两个 P0 问题（**ProfilePage 用列表接口做统计** 和 **SubscriptionsPage 缺 `filter=mine` 导致前端全量过滤**）是最需要后端配合解决的，改完全站接口使用就能完全符合「一主 + 若干辅」原则。