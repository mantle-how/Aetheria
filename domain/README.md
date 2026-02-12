# 邏輯處理

## **world:** 
* **world_model.py:** world狀態模型(時間、全局參數、環境等等)
* **map_generator.py:** 世界生成器(世界seed)
* **rule.py:** 世界規則(天氣、經濟、災害、資源)

## **agent:** 
* **agent_model.py:** 角色模型(狀態、位置、屬性、存活)
* **needs.py:** 需求(飢餓、疲勞、安全、社交、金錢、色慾)
* **personality.py:** 人格特質
* **relationship.py:** 關係模型(信任、好感、敵意、熟悉度)

## **event:** 
* **base.py:** 事件基本屬性(tick、actor、payload schema)
* **world_event.py:** 世界事件定義(地震、暴雨、政策、經濟波動)
* **agent_event.py:** 人物事件定義(移動、對話、受傷、婚姻、生育)
* **codecs.py:** 事件序列化
* **taxonomy.py:** 事件分類統計

## **simulation:** 
* **perception.py:** 感知(視野內的資訊、周圍的聲音)
* **decision_policy:** 決策模型
* **action_system.py:** 行動解析(行動如何更改狀態)
* **conflict_resolution.py:** 衝突處理(搶資源、打架、碰撞時的固定規則)