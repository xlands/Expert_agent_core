# 项目介绍

![HMA架构图](asset/HMA.png)

## 项目优势


1. **多级Agent架构**：采用分层次调用agent的设计模式，从L1到L4层层分工。这种多级架构能够有效解决multi agent的不稳定问题。
   - L1层：ChatBot/Planing Agent具有高度智能，能与人类完成交互
   - L2层：Expert Agent能根据L1意图完成复杂商业逻辑
   - L3层：Tools Agent在上层指导下完成特定简单任务
   - L4层：Tools不具备智能，只是一串代码
   
2. **流程固定化**：将planning生成的流程固定为工作流，提高系统稳定性和可靠性
   - 优化多agent协作的稳定性
   - 减少随机性，保证结果一致性
   - 便于调试和优化系统性能

## 目录
- chatbot:
    - 迎宾机器人：用prompt预先设定背景与可以做什么，当意图不足以进行社媒调研deep research时，进行正常对话或验证意图；当意图清晰时调用query rewriter模块开始向服务端要求数据。
    - 风控机器人：MVP暂时先不做，等后续需要应对监管的时候再做。
- planing系统: 
    - 一期先只是确定需要进行哪些分析：把分析师agent像function call一样喂给planing模型，模型选择需要进行的分析
    - 二期分析师多了之后，要增加planing展示，让用户可以修改关键词和分析内容
- agent: 
    - 一个agent就是一个分析师
    - 一个分析师就是一个行为树
    - 行为树的叶子节点就是一个工具
- tools:
  - 数据获取：从数据库获取已经进行了原子处理的数据
  - 数据处理：进行高维数据分析。
    - 一期先预先定义好分析的内容（分析师行为树）
    - 二期可以让模型根据洞察进行进一步的深度分析（reflection + function call）
  - 数据可视化：将分析结果可视化。这里先改成用prompt直接让模型生成html
- momery:
  - 短期记忆：用户行为。需要增加一个专门的总结模块。
  - 长期记忆：历史的分析结果。需要增加RAG功能
- reflection:
  - 这里需要反思数据是否正确，是否需要补充或者重新分析

## Data
原子化数据处理工具
| 工具函数 | 描述 | 输入 | 输出 |
|---------|------|------|------|
| batch_analyze_brand_mentions | 批量分析品牌提及频次 | 内容列表, LLM实例, 批处理大小 | 品牌提及频次列表 |
| batch_analyze_user_competition | 批量分析用户竞争情况 | 内容列表, LLM实例, 批处理大小 | 用户竞争情况列表 |
| extract_main_brands | 提取主要品牌并准备数据 | 解析后的数据, 品牌提及列表, 完整内容列表 | 品牌列表和对应的内容列表 |
| batch_analyze_sentiment | 批量分析品牌情感和特征 | 内容列表, 品牌列表, LLM实例, 批处理大小 | 情感分析结果列表 |
| batch_analyze_strengths_weaknesses | 批量分析品牌优势和劣势 | 内容列表, 品牌列表, LLM实例, 批处理大小 | 优势劣势分析结果列表 |
| integrate_analysis_results | 整合所有分析结果 | 解析后的数据, 品牌提及分析结果, 用户竞争分析结果, 情感分析结果, 优势劣势分析结果 | 整合后的完整结果 |
| atomic_insights | 增强版内容分析函数，处理已解析的数据列表，使用批量处理提高效率 | 已解析的数据列表 (包含 title, detail_desc, comments 等键的字典列表), 输出目录(可选), 模型ID | 处理后的数据列表 |

## Agents
系统中包含5个专业分析师，每个分析师负责不同维度的数据分析：

1. **BrandAnalyzer (品牌分析师)**
   - 负责分析品牌声量、情感和特征
   - 主要功能：
     - `analyze_brand_mentions`: 分析品牌提及频次和占比，生成品牌声量分析
     - `analyze_brand_sentiment`: 分析品牌情感分布，提取正面、中性和负面评价

2. **CompetitorAnalyzer (竞争分析师)**
   - 负责分析竞争对手和竞争关系
   - 主要功能：
     - `analyze_competitor_relationships`: 分析主品牌与竞争对手的关系，包括用户摇摆和流出情况

3. **FeatureAnalyzer (产品特征分析师)**
   - 使用LLM发现用户真正关心的产品维度
   - 主要功能：
     - `analyze_product_features`: 分析产品特征和各品牌在不同特征上的表现，生成雷达图可视化

4. **KeywordAnalyzer (关键词分析师)**
   - 使用LLM发现真实用户表达
   - 主要功能：
     - `analyze_keywords`: 提取正面和负面关键词，生成词云图可视化

5. **TrendAnalyzer (趋势分析师)**
   - 展示热门帖子和讨论趋势
   - 主要功能：
     - `analyze_trends`: 分析行业趋势，提取热门话题和相关用户原声

6. **IPAnalyzer (IP分析师)**
   - 负责分析用户地理分布
   - 主要功能：
     - `analyze_ip_distribution`: 根据热度加权计算地区分布，区分发帖和评论的地域特征

每个分析师都具有生成数据驱动洞察的能力，并能将分析结果保存为JSON文件。

## Tools

系统中包含多种分析工具，主要分为以下几类：

| 类别 | 工具函数 | 描述 | 输入 | 输出 |
|------|---------|------|------|------|
| **数据提取** | `calculate_brand_mentions` | 计算品牌提及频次和占比 | 原始数据列表 | 品牌名称、提及次数和占比 |
| | `extract_user_quotes` | 提取用户原声，支持按品牌或特征筛选 | 原始数据列表，筛选条件 | 用户原声列表 |
| | `extract_top_k_contents` | 提取最热门的K条内容和评论 | 原始数据列表，K值 | 拼接的内容文本 |
| | `get_top_heat_posts` | 获取热度最高的帖子 | 原始数据列表，数量 | 热度最高的帖子列表 |
| | `calculate_content_heat` | 计算内容热度值 | 内容数据，是否为评论 | 热度值 |
| **LLM分析** | `analyze_content_with_llm` | 使用LLM对内容进行通用分析 | 原始数据，分析类型 | 分析结果 |
| | `calculate_sentiment_distribution` | 计算各品牌的情感分布 | 原始数据列表 | 品牌情感分布 |
| | `extract_feature_dimensions` | 使用LLM提取内容中的特征维度 | 原始数据列表 | 特征维度分析结果 |
| | `extract_keyword_analysis` | 使用LLM提取关键词分析 | 原始数据列表 | 关键词分析结果 |
| | `extract_competitor_relationships` | 使用LLM提取竞争关系分析 | 原始数据列表 | 竞争关系分析结果 |

这些工具函数为分析师提供数据处理和分析能力，支持从原始数据中提取有价值的洞察。每个工具都设计为独立的功能模块，便于扩展和维护。未来可以根据需求继续添加新的工具函数，如时间序列分析(趋势洞察)等。

# AI Agent HTTP Interface Specification

## 流式任务接口

### Endpoint

```
POST /v1/streaming/query
```

### 请求规范

```json
{
  "query_type": "user|server|interrupt",
  "qa_id": 1,
  "user_id": 1,
  "conversation_id": 1,
  "content": {
    // user query。当query_type = user生效，否则不生效
    // 使用 ChatML 类似格式的消息列表
    "messages": [
      {"role": "system", "content": "系统提示词（可选）"},
      {"role": "user", "content": "用户第一轮输入"},
      {"role": "assistant", "content": "助手第一轮回复"},
      {"role": "user", "content": "用户最新输入"}
    ],
    
    // server query（直接传递数据），当query_type = server生效，否则不生效
    "collected_data": [
      {
        "title": string,        // 内容标题
        "detail_desc": string,  // 详细描述/正文内容
        "heat_value": string,   // 热度值
        "comment_count": string, // 评论数量
        "comments": [string],   // 评论列表
        "like_count": string,   // 点赞数量
        "collect_count": string, // 收藏数量
        "author_name": string   // 作者名称(可选)
      }
    ],
    
    // interrupt query，当query_type = interrupt生效，否则不生效
    "interrupt_reason": "user_cancel|timeout"
  }
}
```

### 响应流格式

```json
{
  "qa_id": 1,
  "user_id": 1,
  "conversation_id": 1,
  "task_type": "crawl_task|stream|report|done|error",

  "content": {
    // "content" 字段的结构取决于 "task_type"

    // 当 task_type = "crawl_task" 时 (来自GreetingBot):
    //   "background": "...", "task": "...", "keywords": {...}

    // 当 task_type = "stream" 时 (日志或状态更新):
    //   "content": "[日志前缀] 日志消息字符串..."

    // 当 task_type = "report" 时 (HTML报告行):
    //   "content": "HTML报告的一行字符串..."

    // 当 task_type = "done" 时 (最终执行摘要):
    //   这里 "content" 的值是包含执行结果的完整字典:
    //   {
    //     "status": "success | partial_success | failure",
    //     "message": "执行摘要信息",
    //     "executed_tasks_count": 10,
    //     "failed_tasks": [{"task": "task_name", "error": "error details"}],
    //     "sub_report_paths": ["path/to/data1.json"],
    //     "final_report_path": "path/to/final_report.html | None",
    //     "error": "Overall error message if status is failure | None"
    //   }

    // 当 task_type = "error" 时 (处理中发生的错误):
    //   "error": "错误信息或代码",
    //   "message": "(可选) 更详细的错误描述",
    //   "retryable": true/false // (可选)
  }
}
```

### 示例场景

#### 用户中断请求：

```bash
curl -X POST http://agent.internal/v1/streaming/query \
-H "Content-Type: application/json" \
-d '{
  "query_type": "interrupt",
  "task_id": "7b3f9a2c-01d5-4e8a-b8ae-123456789abc",
  "content": {
    "interrupt_reason": "user_cancel"
  }
}'
```

---

## 数据原子化接口

### Endpoint

```
POST /v1/data/processing
```

### 数据处理流程

#### 请求格式：

```json
{
  "raw_data": [  // 数组类型
    {
      // 通用字段（所有源共有）
      "title": string,                // 内容标题
      "detail_desc": string,          // 详细描述/正文内容
      "heat_value": string,           // 热度值
      "comment_count": string,        // 评论数量
      "like_count": string,           // 点赞数量
      "collect_count": string,        // 收藏数量
      "author_name": string,          // 作者名称
      "author_id": string,            // 作者ID
      "author_homepage_url": string,  // 作者主页链接
      "author_fans_count": string,    // 作者粉丝数
      "author_signature": string,     // 作者签名
      "source": string,               // 来源平台 (如 "xhs", "dy")
      "url": string,                  // 内容链接
      "created_date": string,         // 创建日期
      "location": string,             // 位置信息
      "heat": number,                 // 热度值
      
      // 新格式字段 - 统一评论结构
      "comments_data": [              // 评论数据数组
        {
          "comment_content": string,          // 评论内容
          "comment_user_nick": string,        // 评论用户昵称
          "comment_user_avatar_url": string,  // 评论用户头像URL
          "comment_user_homepage_url": string,// 评论用户主页链接
          "comment_date": string,             // 评论日期
          "comment_location": string,         // 评论位置
          "comment_heat_value": number,       // 评论热度值
          "comment_like_count": number,       // 评论点赞数
          "comment_reply_count": number       // 评论回复数
        }
      ],
      
      // 预分析字段（可选）
      "mentioned_brand": {            // 已有的品牌提及信息
        "brand1": number,             // 品牌名: 提及频率值
        "brand2": number
      },
      
      // 平台特定字段（可选）
      "data_id": string,              // 数据ID
      "image_url": string,            // 图片URL
      "author_recent_content": [string], // 作者最近内容(抖音特有)
      "share_count": string,          // 分享数(抖音特有)
      "crawl_time": string,           // 数据抓取时间
      
      // 历史兼容字段（旧格式，不推荐使用）
      "comments": [string],           // 简单评论列表
      "is_ad": boolean,               // 是否为广告
      "judgment_basis": string        // 判断依据
    }
  ]
}
```

#### 数据源格式说明

系统支持多种数据源，通过请求数据中的`source`字段区分处理逻辑：

1. **小红书数据 (`source="xhs"`)**: 
   - 包含详细的评论结构 `comments_data`
   - 特有 `heat_value`、`collect_count` 等互动数据
   - 评论可能包含地理位置信息

2. **抖音数据 (`source="dy"`)**: 
   - 包含 `author_recent_content` 作者最近发布内容列表
   - 包含 `share_count` 分享数据
   - 评论结构与小红书相同，但更多包含位置与日期信息
   - 评论有更详细的热度和互动指标

#### 预分析数据

如果数据中已包含部分分析结果，系统会优先使用这些结果：

- `mentioned_brand`: 如果已存在此字段，系统将跳过品牌提及分析阶段，直接使用已有数据
- `heat`: 标准化的热度指标 (0-100)，用于跨平台数据比较

#### 响应格式

```json
{
  "content": [  // 数组类型
    {
      // 原始数据字段 (保留所有输入字段)
      "title": string,                // 内容标题
      "detail_desc": string,          // 详细描述/正文内容
      "heat_value": string,           // 热度值
      "comment_count": string,        // 评论数量
      "comments_data": array,         // 评论数据(详细结构)
      "like_count": string,           // 点赞数量
      "collect_count": string,        // 收藏数量
      "author_name": string,          // 作者名称
      "author_id": string,            // 作者ID
      "author_homepage_url": string,  // 作者主页链接
      "author_fans_count": string,    // 作者粉丝数
      "author_signature": string,     // 作者签名
      "source": string,               // 来源平台
      "url": string,                  // 内容链接
      "created_date": string,         // 创建日期
      "location": string,             // 位置信息
      "heat": number,                 // 标准化热度值
      
      // 对于抖音数据，额外保留
      "author_recent_content": array, // 作者最近内容
      "share_count": string,          // 分享数
      
      // 原子化处理添加的字段
      "brand_mentions": {             // 品牌提及情况
        string: number                // 品牌名: 提及次数
      },
      "user_competition": {           // 用户竞争情况分析
        "competition_type": string,   // 竞争类型
        "brand_pairs": [              // 品牌对
          {
            "type": string,           // 关系类型
            "source_brand": string,   // 来源品牌
            "target_brand": string,   // 目标品牌
            "evidence": string        // 原文证据
          }
        ],
        "reason": string              // 分析原因
      },
      "brand_sentiments": {           // 品牌情感分析
        string: string                // 品牌名: 情感倾向
      },
      "brand_features": {             // 品牌特征分析
        string: {                     // 品牌名
          string: string              // 特征: 评价
        }
      },
      "brand_analysis": {             // 品牌优劣势分析
        string: {                     // 品牌名
          "strengths": [              // 优势列表
            {
              "feature": string,      // 特性名称
              "description": string   // 详细描述
            }
          ],
          "weaknesses": [             // 劣势列表
            {
              "feature": string,      // 特性名称
              "description": string   // 详细描述
            }
          ]
        }
      }
    }
  ]
}
```
- 响应会保留原始数据中的所有字段
- 同时添加原子化处理的分析结果字段
- 分析过程会考虑数据来源的特点，对不同平台的数据处理方式略有不同
- 如果数据中已有预分析结果，系统会优先使用这些结果，提高处理效率

### 错误处理

#### 通用错误格式：

```json
{
  "error": {
    "code": string,
    "message": string,
    "retryable": boolean
  }
}
```

#### 常见错误码：

<!-- 此处可添加常见错误码列表 -->

---

## 对话摘要接口

### Endpoint

```
POST /v1/conversation/summary
```

### 请求格式

```json
{
  "conversation_id": "string",  // 可选，用于日志和跟踪
  "messages": [                 // 必需，对话历史
    {
      "role": "user/assistant", 
      "content": "string"
    }
  ],
  "model_id": "string"          // 可选，指定使用的模型
}
```

### 响应格式

```json
{
  "summary": "string",         // 生成的摘要内容
  "conversation_id": "string"  // 返回请求中的会话ID
}
```

### 错误处理

与其他接口使用相同的错误码格式：

```json
{
  "error": {
    "code": string,
    "message": string,
    "retryable": boolean
  }
}
```

---

## 注意事项

### 1. 超时控制：
- User Query：60秒超时
- Server Query：600秒超时
- 原子化处理：30秒超时

### 2. 流式控制：
- 收到interrupt请求后应在5秒内终止任务

### 3. 数据格式：
- 所有字符串字段使用UTF-8编码