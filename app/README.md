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