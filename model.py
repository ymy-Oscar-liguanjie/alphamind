"""风险预测模型加载器
集成 M3 输出的联邦学习模型
"""
import os
import numpy as np
import pandas as pd
import joblib

# 全局模型缓存
_model = None
_used_features = None
_scaler = None

def load_model(workdir="work"):
    """加载 M3 训练的风险预测模型"""
    global _model, _used_features, _scaler
    
    if _model is not None:
        return _model, _used_features, _scaler
    
    try:
        # 加载模型
        model_path = os.path.join(workdir, "risk_model.pkl")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}\n请先运行 M3_fedavg_risk_model.py")
        
        _model = joblib.load(model_path)
        print(f"✅ 已加载模型: {model_path}")
        
        # 加载模型使用的特征列
        features_path = os.path.join(workdir, "used_features_m3.csv")
        if os.path.exists(features_path):
            features_df = pd.read_csv(features_path)
            _used_features = features_df.iloc[:, 0].tolist()  # 第一列为特征名
        else:
            print(f"⚠️  特征列文件不存在: {features_path}")
            _used_features = None
        
        # 尝试加载标准化器
        scaler_path = os.path.join(workdir, "scaler.joblib")
        if os.path.exists(scaler_path):
            _scaler = joblib.load(scaler_path)
        
        return _model, _used_features, _scaler
    
    except Exception as e:
        print(f"❌ 加载模型失败: {e}")
        return None, None, None

def predict_risk(features_dict, workdir="work"):
    """预测用户风险等级
    
    Args:
        features_dict: 特征字典 {特征名: 值}
        workdir: 模型工作目录
        
    Returns:
        risk_prob: 风险概率 (0-1 之间)
    """
    model, used_features, scaler = load_model(workdir)
    
    if model is None:
        raise RuntimeError("模型加载失败")
    
    try:
        # 如果输入是列表或数组，直接使用
        if isinstance(features_dict, (list, np.ndarray)):
            X = np.array(features_dict).reshape(1, -1)
        else:
            # 如果输入是字典，按照模型使用的特征列提取
            if used_features is None:
                raise ValueError("无法获取模型使用的特征列")
            
            # 提取特征
            feature_values = []
            for feat in used_features:
                if feat in features_dict:
                    feature_values.append(features_dict[feat])
                else:
                    feature_values.append(0)  # 缺失特征用0填充
            
            X = np.array(feature_values).reshape(1, -1)
        
        # 标准化（如果有scaler）
        if scaler is not None:
            X = scaler.transform(X)
        
        # 预测
        risk_prob = model.predict_proba(X)[0][1]  # 获取正类概率
        return float(risk_prob)
    
    except Exception as e:
        print(f"❌ 风险预测失败: {e}")
        raise

if __name__ == "__main__":
    # 测试：加载模型
    model, features, scaler = load_model()
    if model:
        print(f"模型类型: {type(model)}")
        print(f"使用特征数: {len(features) if features else 'Unknown'}")