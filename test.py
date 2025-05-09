import csv
file_path = '/Users/trafalgarlaw/project/cotex_ai_agent/data/帮我做一下小米汽车的竞品分析/智能汽车体验.csv'

with open(file_path, mode='r', encoding='utf-8') as csv_file:
    # 使用DictReader自动处理标题行，方便通过列名访问
    csv_reader = csv.DictReader(csv_file)

    print(f"成功打开文件：{file_path}")
    print(f"列标题：{csv_reader.fieldnames}\n")

    for row_num, row in enumerate(csv_reader, 1):
        print(f"第 {row_num} 行数据：")
        for col_name, value in row.items():
            print(f"  {col_name}: {value}")
        print("-" * 30)