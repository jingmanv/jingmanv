# 可测试性设计（Design for Testability）培训材料

> 面向对象：软件设计师 / 中高级研发工程师
> 讲师：资深软件架构师
> 形式：可作为 PPT 大纲，也可直接作为培训文档使用。每一章末尾附"讲师备注 / 讨论问题"，便于互动。

---

## 目录

- 第一章 理论知识：什么是可测试性
- 第二章 实践落地：如何实现可测试性（单元测试 / 组件测试 / 端到端测试）
- 第三章 设计阶段：如何在设计文档中体现可测试性（含具体功能示例）
- **第四章 架构与设计层面的可测试性机制（测试开关 / 探针 / 控制点）**
- 附录 A：可测试性自检清单（Checklist）
- 附录 B：常见反模式（Anti-Patterns）

> 重要提示：可测试性 **不仅是代码层面的事**。它首先是**架构与设计层面的决策**——
> 在画系统图、定模块边界、写接口契约的那一刻，就应该回答："这个东西以后怎么测？"
> 第四章专门讨论这一层级的设计手段，**测试开关（Test Hooks / Switches）** 是其中最典型的例子。

---

# 第一章 理论知识：什么是可测试性

## 1.1 定义

**可测试性（Testability）** 是软件系统的一种**质量属性**（Quality Attribute，ISO/IEC 25010 中归属于"可维护性"子特性），用以衡量：

> 在给定的测试条件下，系统能够被**有效、低成本**地验证其行为是否符合预期的程度。

通俗讲：**写测试有多容易、测试跑得有多快、定位缺陷有多准。**

## 1.2 为什么可测试性重要

| 维度 | 可测试性差 | 可测试性好 |
|---|---|---|
| 缺陷发现成本 | 上线后才暴露 | 提交即拦截 |
| 重构信心 | 不敢动旧代码 | 红绿重构循环 |
| 交付节奏 | 回归测试瓶颈 | CI 数分钟反馈 |
| 团队协作 | 测试依赖个别专家 | 任何人可贡献测试 |
| 架构腐化 | 越来越难加测试 | 测试反向约束架构 |

**核心观点：可测试性不是测试人员的事，而是架构与设计的事。**

## 1.3 可测试性的五大支柱（CIDOR 模型）

| 支柱 | 含义 | 反面例子 |
|---|---|---|
| **C**ontrollability（可控性） | 能否方便地把系统/模块置于任意输入或状态 | 时间、随机数、外部 API 写死在代码里 |
| **I**solability（可隔离性） | 能否单独测试某个模块，不被外部依赖污染 | 业务逻辑里直接 `new DbConnection()` |
| **D**eterminism（确定性） | 同样输入是否总产生同样输出 | 依赖系统时钟、线程调度、HashMap 顺序 |
| **O**bservability（可观察性） | 能否方便地拿到执行后的状态/中间结果 | 关键状态藏在 private 字段且无 getter |
| **R**eadability/Simplicity（简洁性） | 被测对象本身职责是否清晰、易于断言 | 一个方法 500 行、做 8 件事 |

> 助记口诀：**"控、隔、定、观、简"**。设计评审时按此五项打分。

## 1.4 可测试性 vs. 测试覆盖率

- 高覆盖率 ≠ 高可测试性。覆盖率只是结果，**可测试性是因**。
- 一个为了刷覆盖率写的"打桩测试"既不能发现 bug，也不能支持重构，反而成为负债。
- 优先追求**有效断言** + **快速反馈** + **明确失败定位**。

## 1.5 测试金字塔与可测试性的关系

```
         /\
        /E2E\         少量：贵、慢、脆
       /------\
      / 组件/集成 \    适量：验证模块协作
     /------------\
    /   单元测试    \  大量：快、稳、便宜
   /----------------\
```

可测试性差的系统会被迫倒置为**冰淇淋甜筒**：底层难写单元测试 → 只能堆 E2E → 反馈慢 → 测试腐烂 → 大家不敢动代码。

**讲师备注 / 讨论：** 让学员举一个自己项目里"明知应该写单元测试但写不出来"的例子，分析卡在 CIDOR 的哪一项。

---

# 第二章 实践落地：如何实现可测试性

## 2.1 总体策略

1. **依赖倒置**：让业务逻辑依赖抽象（接口），运行时注入实现。
2. **纯函数优先**：把"计算"和"副作用"分离（Functional Core, Imperative Shell）。
3. **可注入的边界**：时间、随机数、ID 生成、网络、文件、消息队列、配置都视作"依赖"。
4. **稳定的契约**：模块之间用清晰的接口定义协作，便于打桩（stub）和模拟（mock）。
5. **测试分层**：单元、组件/集成、端到端，按金字塔分配资源。

## 2.2 单元测试（Unit Test）

**目标**：验证**单个类/函数**的逻辑，不依赖外部资源，毫秒级返回。

### 反例（不可测试）

```java
public class OrderService {
    public BigDecimal checkout(Long userId) {
        // 直接 new 数据库连接
        var conn = DriverManager.getConnection("jdbc:mysql://prod/...");
        var user = new UserDao(conn).find(userId);
        // 直接调静态方法获取当前时间
        if (LocalDate.now().getDayOfWeek() == DayOfWeek.FRIDAY) {
            // 直接调用第三方 HTTP
            var rate = new HttpClient().get("https://api.fx.com/rate");
            return user.balance().multiply(rate);
        }
        return user.balance();
    }
}
```

问题：违反 CIDOR 中的 **C/I/D**。无法在不连数据库、不联网、不等到周五的情况下测试。

### 正例（依赖注入 + 时钟抽象）

```java
public class OrderService {
    private final UserRepository userRepo;
    private final FxRateClient fxClient;
    private final Clock clock;        // 注入时钟，可控！

    public OrderService(UserRepository u, FxRateClient f, Clock c) {
        this.userRepo = u; this.fxClient = f; this.clock = c;
    }

    public BigDecimal checkout(Long userId) {
        var user = userRepo.find(userId);
        if (LocalDate.now(clock).getDayOfWeek() == DayOfWeek.FRIDAY) {
            return user.balance().multiply(fxClient.currentRate());
        }
        return user.balance();
    }
}
```

测试：

```java
@Test
void shouldApplyFxRateOnFriday() {
    var fixedClock = Clock.fixed(Instant.parse("2026-06-26T10:00:00Z"), UTC); // 周五
    var svc = new OrderService(
        userId -> new User(userId, new BigDecimal("100")),  // stub
        () -> new BigDecimal("1.2"),                        // stub
        fixedClock);

    assertEquals(new BigDecimal("120.0"), svc.checkout(1L));
}
```

### 单元测试要点

- **FIRST 原则**：Fast / Independent / Repeatable / Self-validating / Timely。
- 一个测试只验证**一个行为**，命名采用 `should_<expected>_when_<condition>`。
- 用 **AAA 结构**：Arrange–Act–Assert。
- 避免在单元测试里启动 Spring 容器、连数据库、连网络。
- Mock 用于**外部协作者**（DB、HTTP），**不要 mock 你自己的值对象**。

## 2.3 组件 / 集成测试（Component / Integration Test）

**目标**：在**真实运行环境的部分子集**中，验证多个模块协作的正确性。

典型场景：
- Repository + 真实数据库（用 **Testcontainers** 启动 PostgreSQL）
- HTTP Controller + Service + 内存数据库
- 消息消费者 + 真实 Kafka（Testcontainers）

### 示例：Spring Boot + Testcontainers

```java
@SpringBootTest
@Testcontainers
class OrderRepositoryIT {

    @Container
    static PostgreSQLContainer<?> pg = new PostgreSQLContainer<>("postgres:16");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", pg::getJdbcUrl);
        r.add("spring.datasource.username", pg::getUsername);
        r.add("spring.datasource.password", pg::getPassword);
    }

    @Autowired OrderRepository repo;

    @Test
    void savesAndLoadsOrder() {
        var saved = repo.save(new Order(null, "SKU-1", 2));
        assertEquals(saved.id(), repo.findById(saved.id()).orElseThrow().id());
    }
}
```

### 组件测试要点

- 用 **Testcontainers** 替代 H2 等"内存替身"，避免"测试通过，生产挂掉"。
- 每个用例**自管理数据**（建表/清表/事务回滚），保证可重复。
- 关注**协作契约**：序列化、SQL 方言、事务边界、消息格式。
- 对外部第三方 API：用 **WireMock** / **MockServer** 录制和回放契约。

## 2.4 端到端测试（E2E Test）

**目标**：从用户视角验证关键业务流程在真实部署形态下的正确性。

### 前端 E2E（Playwright 示例）

```ts
test('用户可以下单并看到订单号', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('用户名').fill('alice');
  await page.getByLabel('密码').fill('correct horse');
  await page.getByRole('button', { name: '登录' }).click();

  await page.getByRole('link', { name: '商品 A' }).click();
  await page.getByRole('button', { name: '加入购物车' }).click();
  await page.getByRole('button', { name: '结算' }).click();

  await expect(page.getByTestId('order-id')).toBeVisible();
});
```

### 后端 E2E（接口层）

通过 HTTP 调用部署在测试环境的真实服务，串起 **登录 → 下单 → 支付回调 → 查询订单** 的链路。

### E2E 要点

- **数量克制**：只覆盖核心黄金路径（Critical User Journey），通常 < 50 条。
- **数据隔离**：每个用例用独立账号/租户，避免相互踩。
- **稳定性**：消灭 `sleep(3000)`，使用基于**条件等待**的 API（`waitFor`、`expect.toBeVisible`）。
- **可定位**：UI 元素使用稳定的 `data-testid`，不要依赖文案或 CSS 类。
- **可观察**：失败时自动截图、录屏、保留日志和 trace。

## 2.5 其他重要实践

| 实践 | 解决的问题 | 工具示例 |
|---|---|---|
| **契约测试**（Contract Test） | 微服务上下游接口漂移 | Pact, Spring Cloud Contract |
| **快照测试**（Snapshot） | UI/序列化结果回归 | Jest, ApprovalTests |
| **属性测试**（Property-based） | 边界与组合爆炸 | jqwik, Hypothesis, fast-check |
| **变异测试**（Mutation） | 断言力度不够 | PIT, Stryker |
| **可观测性内建** | 线上问题难定位 | OpenTelemetry, 结构化日志 |
| **Feature Flag** | 灰度与可控回滚 | Unleash, LaunchDarkly |

**讲师备注 / 讨论：** 让学员在自己项目里找一个 `LocalDateTime.now()` 或 `Math.random()` 的调用点，讨论如何重构为可注入的依赖。

---

# 第三章 设计阶段：如何在设计文档中体现可测试性

> 核心理念：**可测试性必须在设计阶段就被显式定义，而不是等编码完再补救。**
> 在设计文档（HLD/LLD）中应有**专门的"可测试性"章节**。

## 3.1 设计文档中的"可测试性"章节模板

建议在设计文档中加入如下结构化小节：

```
## 6. 可测试性设计（Testability Design）
  6.1 测试策略与分层目标（单元/组件/E2E 比例与覆盖目标）
  6.2 被测边界（Seam）定义：列出所有外部依赖及其抽象接口
  6.3 可控性设计：时间、随机、ID、配置、Feature Flag 注入方式
  6.4 可观察性设计：日志/指标/事件、关键状态暴露方式
  6.5 测试数据与环境：数据构造器、Testcontainers、Mock 服务
  6.6 关键场景的测试用例清单（含异常与边界）
  6.7 非功能测试：性能、并发、故障注入（Chaos）
```

## 3.2 设计原则清单（设计评审时使用）

1. **每个外部依赖必须有抽象接口**（数据库、HTTP、MQ、文件、时钟、随机、当前用户）。
2. **构造函数注入优先**，避免静态方法、单例、`ServiceLocator`。
3. **副作用集中在边界层**，核心领域逻辑保持为纯函数。
4. **关键状态/事件必须可观察**（领域事件、结构化日志、指标）。
5. **配置外置**：环境差异通过配置注入，而不是 `if (env == "prod")`。
6. **Feature Flag 默认配套**：新功能上线必须可远程关闭，便于线上 A/B 与回滚验证。
7. **明确幂等性**：写操作要么天然幂等，要么提供幂等键（idempotency key），便于重试与重放测试。
8. **错误必须可枚举**：用错误码/异常体系替代裸 `RuntimeException`，便于断言。

## 3.3 举例说明 1：优惠券核销功能（CouponRedemption）

### 需求

用户在下单时使用优惠券，需校验：券有效、未使用、用户有权使用、金额满足门槛；成功后扣减库存并记录核销流水。

### 不考虑可测试性的设计（反例）

- 直接在 `OrderController` 里查 DB、调风控 HTTP、写 Redis 计数。
- 用 `System.currentTimeMillis()` 判断券是否过期。
- 用 `UUID.randomUUID()` 生成核销流水号。
- 异常统一抛 `RuntimeException("券不可用")`。

后果：无法单元测试过期边界；无法验证幂等；测试断言只能匹配字符串；CI 必须依赖真实 Redis。

### 考虑可测试性的设计

**模块划分（Seam）：**

| 接口 | 职责 | 测试时替身 |
|---|---|---|
| `CouponRepository` | 读取/更新券状态 | In-memory fake |
| `RiskClient` | 调用风控服务 | WireMock / Stub |
| `Clock` | 提供当前时间 | `Clock.fixed(...)` |
| `IdGenerator` | 生成核销流水号 | 固定序列 stub |
| `RedemptionEventPublisher` | 发布领域事件 | 内存收集器，便于断言 |

**对外提供的可测试性参数 / 接口：**

1. **构造参数**：上述 5 个依赖通过构造函数注入。
2. **领域事件**：成功核销发布 `CouponRedeemedEvent(couponId, userId, orderId, redeemedAt, traceId)`，测试可订阅该事件做断言，**无需查 DB**。
3. **幂等键**：`redeem(orderId, couponCode, idempotencyKey)`，重复调用返回相同结果，便于"重放测试"。
4. **明确错误类型**：`CouponExpiredException` / `CouponAlreadyUsedException` / `RiskRejectedException` / `ThresholdNotMetException`，每类一个测试用例。
5. **可观察指标**：暴露 `coupon_redeem_total{result="success|expired|used|risk_rejected"}` 计数器，组件测试可对指标做断言。
6. **Feature Flag**：`coupon.redeem.v2.enabled`，用于灰度新规则，便于 A/B 测试。
7. **Dry-run 模式**：`redeem(..., dryRun=true)` 只校验不落库，便于在生产/预发做"只读探针"。

**测试用例清单（写进设计文档）：**

| # | 场景 | 层级 | 关键断言 |
|---|---|---|---|
| 1 | 正常核销 | 单元 | 返回成功 + 发布 `CouponRedeemedEvent` |
| 2 | 券已过期（边界：到期时刻前 1ms / 后 1ms） | 单元 | 抛 `CouponExpiredException` |
| 3 | 重复核销同一 idempotencyKey | 单元 | 返回首次结果，不重复扣减 |
| 4 | 风控拒绝 | 单元 | 抛 `RiskRejectedException`，指标 +1 |
| 5 | 并发核销同一券 | 组件 | 仅一笔成功，其余失败（DB 乐观锁验证） |
| 6 | 用户在 Web 端完整下单使用券 | E2E | 订单金额正确减免，券状态变为已用 |

## 3.4 举例说明 2：定时账单生成（BillingJob）

### 需求

每月 1 号 00:05 跑批，为所有活跃用户生成上月账单。

### 关键可测试性设计

| 设计点 | 说明 |
|---|---|
| **时间注入** | 提供 `generate(YearMonth period)` 接口，调度器只负责传入 `YearMonth.now(clock).minusMonths(1)`。测试时直接传 `YearMonth.of(2026, 5)`，无需等到月初。 |
| **批次可分片** | `generate(period, shard)`，便于按用户 ID 取模分片，单测可只跑 1 个分片。 |
| **断点续跑** | 持久化 `BillingRun(id, period, status, lastProcessedUserId)`，失败重跑幂等。测试可断言中断后恢复。 |
| **Dry-run** | `generate(period, dryRun=true)` 只计算不落库，用于预发回归。 |
| **事件输出** | 每生成一张账单发布 `BillInvoicedEvent`，测试通过事件断言，避免查 DB。 |
| **可观察** | 暴露 `billing_job_duration_seconds`、`billing_job_failed_total`，便于线上验证与告警测试。 |
| **故障注入钩子** | 提供 `BillingHooks.beforeCommit`（测试专用），便于在组件测试里模拟"提交瞬间宕机"。 |

### 设计文档中应明确写出的"测试钩子（Test Hooks）"

> 注意：测试钩子必须**清晰标记为测试专用**，并通过包可见性 / Feature Flag 限制在生产中被滥用。

## 3.5 设计评审中的"可测试性"提问清单

在设计评审时，架构师应至少问以下问题：

1. 这个模块的**外部依赖**有哪些？是否每个都有抽象接口？
2. **时间、随机、ID** 从哪里来？测试时如何替换？
3. 关键的**状态变更**对外可观察吗（事件 / 日志 / 指标）？
4. 失败时抛什么**异常 / 返回什么错误码**？是否便于断言？
5. 是否**幂等**？重试会不会出问题？测试如何覆盖？
6. 是否需要 **Feature Flag**？灰度策略是什么？
7. **测试数据**如何构造？是否提供 Builder / Fixture？
8. 单元、组件、E2E 各覆盖哪些场景？**测试金字塔**比例合理吗？
9. 性能 / 并发 / 故障场景如何测试？
10. 这段代码**三个月后新人能不能写出测试**？

**讲师备注 / 讨论：** 拿出团队近期一份真实设计文档，按以上 10 问做一次现场评审。

---

# 第四章 架构与设计层面的可测试性机制

> **核心观点：可测试性 ≠ 单元测试技巧。**
> 它首先是一系列**架构决策**：在系统里**主动预留**控制点、观察点、隔离点、回放点、开关点。
> 这些机制在需求/设计阶段就要被显式定义，**写进设计文档、画进架构图、纳入接口契约**。
> 一旦上线后再加，代价是 10 倍以上。

## 4.1 为什么"代码层面"不够

代码层面的技巧（DI、Mock、纯函数）解决的是 **"某个类好不好测"**。但下列问题**只能在架构层面**解决：

| 难题 | 代码层面束手无策的原因 |
|---|---|
| 线上某条链路的真实行为是否符合设计？ | 单测覆盖不到分布式时序与真实数据 |
| 新版本风险大，如何只对 1% 用户开启？ | 需要全局开关而非局部分支 |
| 测试环境如何模拟"支付超时"？ | 需要在网关/适配层注入故障 |
| 故障复盘时如何"重放"那条请求？ | 需要请求录制 + 回放基础设施 |
| 压测时如何让流量进入系统但不真扣钱？ | 需要"影子模式 / 影子库" |
| 多团队并行开发时如何不互相阻塞？ | 需要契约 + Mock Server 基础设施 |

> 一句话：**代码可测性让你能写测试，架构可测性让你能在真实系统里持续验证。**

## 4.2 设计层面的六类可测试性机制

下表是设计师在做架构设计时**必须考虑**的六大机制。建议作为设计评审的固定议题。

| 机制 | 解决的问题 | 关键设计元素 |
|---|---|---|
| **1. 测试开关 / Feature Flag** | 上线即可灰度、可关闭、可在生产做 A/B | 配置中心、按用户/租户/百分比的开关引擎 |
| **2. 可控制点（Control Points）** | 让测试能精确驱动系统进入指定状态 | 内部命令接口、时间/随机/ID 注入点 |
| **3. 可观察点（Observability Points）** | 让测试和运维能"看见"内部状态 | 结构化日志、指标、领域事件、TraceID |
| **4. 隔离与替身基础设施** | 让某个子系统能脱离上下游单独测试 | 适配器层、Mock Server、契约测试平台 |
| **5. 录制与回放（Record & Replay）** | 用生产真实流量验证新版本 | 流量镜像、影子库、回放工具 |
| **6. 故障注入点（Fault Injection Hooks）** | 主动验证系统在异常下的行为 | Chaos 平台、网关级故障注入、超时/丢包开关 |

---

## 4.3 重点机制详解

### 4.3.1 测试开关（Test Hooks / Switches）

**定义**：在系统中**显式预留**的、可在运行时打开/关闭某种行为的入口。它不是"调试代码"，而是**架构契约的一部分**。

#### 四类常见测试开关

| 类型 | 用途 | 示例 |
|---|---|---|
| **行为开关（Behavior Switch）** | 切换两套实现，便于对比验证 | `pricing.engine=v1 / v2` |
| **旁路开关（Bypass Switch）** | 跳过外部依赖，便于隔离测试 | `risk.check.enabled=false`（预发跳过风控） |
| **观察开关（Observation Switch）** | 临时打开详细日志/追踪 | `order.trace.verbose=true`（仅对某 traceId 生效） |
| **故障注入开关（Fault Switch）** | 主动制造异常，验证容错 | `payment.gateway.latency.injectMs=3000` |

#### 设计原则（写进设计文档！）

1. **显式声明，而非隐藏**：每一个开关都要在设计文档的"测试开关清单"中登记：名称、用途、默认值、生效范围（全局/租户/用户/请求）、谁可以改、是否允许生产使用。
2. **默认安全**：默认值必须等于"生产正常行为"，开关丢失/配置中心宕机时系统仍然安全。
3. **作用域可控**：优先支持"按请求级"开关（通过 HTTP Header / Context 传递），避免全局开关误伤。
4. **可观察**：每次开关命中要打点（指标 + 日志），防止"打开了忘记关"。
5. **生命周期管理**：开关分两类——**长期开关**（如灰度能力，长期保留）和**临时开关**（发布完成后必须清理）。设计文档要写明类别和清理责任人。
6. **权限与审计**：生产开关必须有审批与审计记录，禁止任何人随手改。
7. **禁区**：开关**绝不能**用来绕过安全/合规校验（鉴权、加密、审计日志）。这是红线。

#### 反模式

- 在代码里散落 `if (System.getProperty("test") != null)` —— 散乱、不可观察、不可审计。
- 测试开关复用业务字段（如 `userId=999 就跳过校验`）—— 极易被攻击。
- 开关无人清理，半年后没人知道它的作用 —— 成为定时炸弹。

#### 示例：支付网关的测试开关清单（设计文档片段）

| 开关名 | 类型 | 默认 | 作用域 | 用途 | 类别 | 责任人 |
|---|---|---|---|---|---|---|
| `payment.gateway.provider` | 行为 | `unionpay` | 全局 | 切换支付通道 | 长期 | 支付组 |
| `payment.gateway.mock.enabled` | 旁路 | `false` | 请求级（Header `X-Test-Mock: true` 且仅白名单账号生效） | 联调时用 Mock 通道，不真实扣款 | 长期 | 支付组 |
| `payment.gateway.latency.injectMs` | 故障注入 | `0` | 请求级（白名单） | 模拟通道慢响应 | 长期 | SRE |
| `payment.refund.v2.enabled` | 行为 | `false` | 按租户百分比 | 新版退款逻辑灰度 | 临时（发布完成后 1 个月内清理） | 张三 |
| `payment.trace.verbose` | 观察 | `false` | 按 traceId | 排障时打开详细日志 | 长期 | SRE |

### 4.3.2 可控制点（Control Points）

让外部能精确驱动系统状态，常见设计手段：

- **管理接口（Admin API）**：暴露受保护的内部命令，如 `POST /internal/jobs/billing/run?period=2026-05`，让测试可手工触发批处理，无需等定时器。
- **时间快进接口**（仅测试环境）：`POST /test/clock/advance?seconds=86400`，配合 `Clock` 抽象，整个系统时间可控。
- **状态构造接口（Test Fixture API）**：`POST /test/fixtures/user`，一次创建包含订单、优惠券、积分的完整测试数据，比起从 UI 一步步点击快 100 倍。
- **种子化随机源**：所有随机/ID 来自统一 `RandomSource`，测试可设置固定 seed，使结果可复现。
- **可暂停的工作流**：长流程引擎（如审批、订单状态机）暴露 `pause/resume/jumpTo` 接口（仅测试环境），便于卡到任意中间状态做断言。

> **关键设计要求**：管理接口必须有独立鉴权 + 网络隔离（仅内网/仅测试集群），并在网关层禁止生产暴露。

### 4.3.3 可观察点（Observability Points）

> "如果测试无法观察到行为，那它就无法断言行为。" — 这是设计层面要解决的问题。

- **领域事件优先于日志**：关键状态变化以事件形式发布（`OrderPaidEvent`、`CouponRedeemedEvent`），测试订阅事件即可断言，无需查 DB。
- **TraceID 贯穿全链路**：每个请求一个 ID，跨服务/跨消息/跨线程透传，E2E 测试可拿 traceId 在 Jaeger/Zipkin 验证调用拓扑。
- **结构化日志**：JSON 化、字段稳定，测试和告警都能解析。
- **健康/状态端点**：`/actuator/health`、`/internal/state` 暴露内部关键状态（缓存命中率、队列深度等），可作为断言点。
- **业务指标 SLI**：`order_success_total`、`payment_latency_seconds` 这些指标本身就是测试的断言对象（"压测后成功率 ≥ 99.9%"）。

### 4.3.4 隔离与替身基础设施

设计层面要回答："当上游/下游还没就绪时，我怎么测？"

- **适配器层 / 防腐层（ACL）**：所有外部系统调用都通过本地适配器接口，便于替换为 Fake/Mock。
- **共享 Mock Server**：团队维护一个长期运行的 WireMock/MockServer 实例，提供常用上游的稳定 Mock，避免每个项目自己造。
- **契约测试平台（Pact Broker 等）**：上下游通过契约约束彼此，避免"集成时才发现接口不匹配"。
- **In-memory 实现**：对数据库/MQ，设计接口时同时提供 `InMemoryXxxRepository`（产品代码包内），既能加速测试也能作为开发期 demo。

### 4.3.5 录制与回放（Record & Replay）

让生产真实流量成为最强的测试用例：

- **流量镜像（Traffic Mirroring / Shadowing）**：网关把生产流量复制一份发到新版本服务，**不返回响应给用户**，对比新旧版本输出差异。
- **影子库（Shadow DB）**：新版本写入到影子库，比对结果但不影响主库。常用于大规模重构验证。
- **请求录制**：在网关或服务入口记录请求 + 响应（脱敏后），定期回放到测试环境作为"真实回归集"。
- **设计要求**：所有对外接口设计之初就要考虑**幂等性**和**可重放性**（带 idempotencyKey、避免依赖"当前时间"的副作用），否则回放就是放炮。

### 4.3.6 故障注入点（Fault Injection Hooks）

可靠性测试不能靠"祈祷线上不出问题"，要主动设计注入点：

- **网关/Service Mesh 级**：在 Istio/Envoy 配置层注入延迟、HTTP 5xx、连接断开。
- **客户端 SDK 内置**：DB/HTTP/MQ 客户端封装时预留 `FaultInjector` 钩子，测试时可让"第 3 次调用必失败"。
- **Chaos 工程平台**：ChaosBlade、Chaos Mesh 等定期演练（杀 Pod、断网、CPU 打满）。
- **设计要求**：每个**对外依赖**在设计文档里都要有"故障场景表"：超时怎么办、5xx 怎么办、部分成功怎么办，并且每个场景都要有对应的注入手段和测试用例。

---

## 4.4 综合案例：支付服务的设计层面可测试性

以"支付服务"为例，演示设计文档中**架构层面的可测试性章节**应该写什么：

### 4.4.1 架构图上的可测试性元素

```
              ┌────────────────────────┐
   用户流量──►│  API Gateway（流量镜像/   │──► 支付服务 v1（生产）
              │  故障注入 / TraceID 入口）│──► 支付服务 v2（影子，只对比不返回）
              └────────────────────────┘
                         │
                         ▼
              ┌────────────────────────┐
              │ 配置中心：Feature Flag    │
              │  - provider=unionpay     │
              │  - mock.enabled=false    │
              │  - refund.v2=10% 灰度    │
              └────────────────────────┘
                         │
   支付服务 ──► 适配器层 ──┼──► 真实银联网关（生产）
                         └──► Mock 支付网关（测试 / 联调）
                         └──► 故障注入代理（演练）
```

### 4.4.2 设计文档应包含的可测试性条目

1. **测试开关清单**（见 4.3.1 表格）。
2. **可控制点**：
   - `POST /internal/payments/{id}/retry` 手工触发重试（仅内网，受 RBAC 控制）。
   - `POST /test/payments/_callback` 模拟银联异步回调（仅测试环境）。
3. **可观察点**：
   - 领域事件：`PaymentInitiatedEvent`、`PaymentSucceededEvent`、`PaymentFailedEvent`，发布到 Kafka topic `payment.events`。
   - 指标：`payment_request_total{provider,result}`、`payment_latency_seconds`。
   - TraceID：从网关注入，透传到银联请求 Header `X-Trace-Id`。
4. **隔离设施**：
   - 适配器接口 `PaymentGateway`，实现包括 `UnionpayGateway` / `MockGateway` / `FaultyGateway`。
   - 契约：与"订单服务"之间用 Pact 维护契约测试。
5. **录制回放**：
   - 网关配置 1% 流量镜像到 v2，对比新旧版本响应（diff 工具），不返回用户。
6. **故障场景表**：

| 场景 | 注入手段 | 期望行为 | 测试用例 |
|---|---|---|---|
| 银联响应超时 5s | `latency.injectMs=5000` | 服务在 3s 超时，记录失败事件，触发重试 | IT-PAY-001 |
| 银联返回 503 | `error.injectRate=1.0` | 服务标记请求为"待人工核对"，不重复扣款 | IT-PAY-002 |
| 异步回调丢失 | 关闭 Mock 回调 | 30 分钟后对账任务自动补偿 | E2E-PAY-003 |
| 重复回调 | 同一回调发送 3 次 | 仅一次生效（幂等），其余幂等返回 | IT-PAY-004 |

### 4.4.3 设计评审时必问的"架构可测试性"问题

1. 这个新模块**预留了哪些测试开关**？默认值是什么？什么时候清理？
2. 测试如何**精确把它驱动到某个中间状态**（控制点）？
3. 测试如何**观察**到行为是否正确（事件 / 指标 / 日志）？
4. **上游/下游还没就绪时**怎么测？有 Mock / 契约 / In-memory 实现吗？
5. 上线后能不能**用真实流量做影子验证**？
6. 出现外部依赖故障时的行为是否在**故障场景表**里有覆盖？
7. 这些机制本身**是否会被滥用为安全后门**？权限和审计够吗？

## 4.5 测试开关的治理（Governance）

测试开关是把双刃剑——用得好是利器，用得乱是灾难。建议团队建立以下治理机制：

- **统一注册中心**：所有开关集中登记（owner、用途、类型、默认值、过期时间）。
- **过期告警**：临时开关到期未清理自动告警，CI 检测代码中是否仍在使用。
- **生产变更审批**：生产开关变更走审批 + 审计。
- **安全红线**：禁止用开关绕过鉴权、加密、审计。代码审查时自动扫描敏感开关名（如 `*.auth.skip`、`*.security.bypass`）。
- **可观察**：每次开关命中打点，便于发现"误开"。
- **演练**：定期"关掉旁路开关跑一次回归"，确保旁路逻辑不腐烂。

**讲师备注 / 讨论：** 让学员列举所在系统目前有哪些"隐式的测试开关"（例如靠改 hosts、改配置文件、写 magic 账号实现的临时旁路），并讨论如何把它们升级为"显式、登记在册、有治理"的设计层开关。

---

# 附录 A：可测试性自检清单（Checklist）

在 PR / 设计评审时使用：

**代码层面：**
- [ ] 没有在业务代码中使用 `new` 创建外部资源（DB、HTTP、文件）
- [ ] 没有使用 `LocalDateTime.now()` / `System.currentTimeMillis()` / `Math.random()` / `UUID.randomUUID()` 等不可控调用（已通过 `Clock` / `IdGenerator` / `RandomSource` 注入）
- [ ] 没有 `static` 业务方法或全局可变状态
- [ ] 每个 public 方法至少 1 个正向 + 1 个反向 + 1 个边界用例
- [ ] 异常类型明确，单独可被断言
- [ ] 单元测试运行时间 < 100ms / 用例
- [ ] CI 中单元测试可在 5 分钟内跑完

**设计 / 架构层面：**
- [ ] 设计文档中**有独立的"可测试性"章节**
- [ ] 列出了**测试开关清单**（名称、类型、默认值、作用域、生命周期、责任人）
- [ ] 每个外部依赖有**适配器接口**，可替换为 Mock/Fake
- [ ] 提供了**管理接口 / Fixture 接口**，便于测试驱动到指定状态
- [ ] 关键状态变化通过**领域事件**对外发布，便于断言
- [ ] 关键链路有 **TraceID** 贯穿，可被 E2E / 线上排障使用
- [ ] 写操作幂等，或提供幂等键，支持重放
- [ ] 有**故障场景表**，每个场景有注入手段与测试用例
- [ ] 测试开关有**治理机制**（登记、过期告警、审计、安全红线）
- [ ] 新增/修改的接口在设计文档中有"可测试性"小节

# 附录 B：常见反模式

| 反模式 | 症状 | 改进方向 |
|---|---|---|
| **God Object** | 一个类几千行，依赖一堆 | 拆分职责，按上下文分模块 |
| **Hidden Time Bomb** | 代码里写死 `now()` | 注入 `Clock` |
| **Sleep-driven Test** | 测试里大量 `Thread.sleep` | 用事件 / 条件等待 |
| **Mock Everything** | 测试断言全是 `verify(mock)` | 改为断言**行为结果**（状态、事件） |
| **Test on Prod Only** | 只能上线后验证 | 引入 Testcontainers、契约测试、Dry-run |
| **Snowflake Env** | 测试环境手工搭建、独一份 | IaC + 容器化，秒级拉起 |
| **Ice-cream Cone** | E2E 多、单元少 | 倒过来，先补单元 |

---

## 培训交付建议

1. **第 1 天上午**：第一章理论 + CIDOR 模型小测验。
2. **第 1 天下午**：第二章实战，分组动手把一段"难测代码"重构为可测代码（建议提供一份示例工程）。
3. **第 2 天上午**：第三章设计，按学员真实项目做一次设计文档"可测试性"小节补写。
4. **第 2 天下午**：设计评审实战 + 自检清单落地到团队 PR 模板。

> **一句话总结：好的架构不是写出来的，是测出来的；可测试性，是设计师的必修课。**
