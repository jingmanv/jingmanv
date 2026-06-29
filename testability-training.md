# 可测试性设计（Design for Testability）培训材料

> 面向对象：软件设计师 / 中高级研发工程师
> 讲师：资深软件架构师
> 形式：可作为 PPT 大纲，也可直接作为培训文档使用。每一章末尾附"讲师备注 / 讨论问题"，便于互动。

---

## 目录

- 第一章 理论知识：什么是可测试性
- 第二章 实践落地：如何实现可测试性（单元测试 / 组件测试 / 端到端测试）
- 第三章 设计阶段：如何在设计文档中体现可测试性（含具体功能示例）
- 附录 A：可测试性自检清单（Checklist）
- 附录 B：常见反模式（Anti-Patterns）

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

# 附录 A：可测试性自检清单（Checklist）

在 PR / 设计评审时使用：

- [ ] 没有在业务代码中使用 `new` 创建外部资源（DB、HTTP、文件）
- [ ] 没有使用 `LocalDateTime.now()` / `System.currentTimeMillis()` / `Math.random()` / `UUID.randomUUID()` 等不可控调用（已通过 `Clock` / `IdGenerator` / `RandomSource` 注入）
- [ ] 没有 `static` 业务方法或全局可变状态
- [ ] 每个 public 方法至少 1 个正向 + 1 个反向 + 1 个边界用例
- [ ] 异常类型明确，单独可被断言
- [ ] 关键状态变更有领域事件 / 结构化日志
- [ ] 写操作幂等，或提供幂等键
- [ ] 单元测试运行时间 < 100ms / 用例
- [ ] CI 中单元测试可在 5 分钟内跑完
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
