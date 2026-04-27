from sklearn.ensemble import RandomForestClassifier
import numpy as np

# 简单模拟训练数据
X = np.random.rand(100, 5)
y = np.random.choice(["保守", "稳健", "激进"], 100)

model = RandomForestClassifier()
model.fit(X, y)

def predict_risk(features):
    return model.predict([features])[0]