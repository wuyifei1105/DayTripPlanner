/**
 * API服务模块
 */

const API_BASE_URL = 'http://localhost:8000';

const api = {
    /**
     * 创建行程规划
     * @param {string} location - 目的地
     * @param {string} startTime - 出发时间
     * @param {string[]} preferences - 偏好标签
     * @returns {Promise<object>}
     */
    async createPlan(location, startTime = '09:00', preferences = []) {
        const response = await fetch(`${API_BASE_URL}/api/plan`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                location,
                start_time: startTime,
                preferences,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '请求失败');
        }

        return await response.json();
    },

    /**
     * 健康检查
     * @returns {Promise<boolean>}
     */
    async healthCheck() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/health`);
            return response.ok;
        } catch {
            return false;
        }
    },
};
