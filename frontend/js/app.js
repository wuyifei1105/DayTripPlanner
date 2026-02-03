/**
 * 主应用逻辑
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM元素
    const searchForm = document.getElementById('searchForm');
    const locationInput = document.getElementById('locationInput');
    const startTimeInput = document.getElementById('startTime');
    const searchBtn = document.getElementById('searchBtn');
    const statusSection = document.getElementById('statusSection');
    const statusMessages = document.getElementById('statusMessages');
    const placesSection = document.getElementById('placesSection');
    const placesList = document.getElementById('placesList');
    const placeCount = document.getElementById('placeCount');
    const timelineSection = document.getElementById('timelineSection');
    const timeline = document.getElementById('timeline');
    const tripSummary = document.getElementById('tripSummary');

    // 状态
    let isLoading = false;
    let currentPlaces = [];
    let currentPlan = null;

    /**
     * 设置加载状态
     */
    function setLoading(loading) {
        isLoading = loading;
        searchBtn.disabled = loading;

        const btnText = searchBtn.querySelector('.btn-text');
        const btnLoading = searchBtn.querySelector('.btn-loading');

        if (loading) {
            btnText.style.display = 'none';
            btnLoading.style.display = 'inline-flex';
        } else {
            btnText.style.display = 'inline';
            btnLoading.style.display = 'none';
        }
    }

    /**
     * 添加状态消息
     */
    function addStatusMessage(message) {
        statusSection.style.display = 'block';
        const p = document.createElement('p');
        p.textContent = message;
        statusMessages.appendChild(p);
        statusMessages.scrollTop = statusMessages.scrollHeight;
    }

    /**
     * 清除状态消息
     */
    function clearStatusMessages() {
        statusMessages.innerHTML = '';
    }

    /**
     * 渲染地点列表
     */
    function renderPlaces(places) {
        currentPlaces = places;
        placesSection.style.display = 'block';
        placeCount.textContent = places.length;

        placesList.innerHTML = places.map((place, index) => {
            const isFood = place.category === '美食';
            return `
                <div class="place-card" data-index="${index}">
                    <div class="place-card-header">
                        <span class="place-name">${place.name}</span>
                        <span class="place-category ${isFood ? 'food' : ''}">${place.category || '景点'}</span>
                    </div>
                    <div class="place-meta">
                        ${place.rating ? `<span class="place-rating">⭐ ${place.rating}</span>` : ''}
                        ${place.price_range ? `<span>💰 ${place.price_range}</span>` : ''}
                        ${place.likes ? `<span>❤️ ${formatNumber(place.likes)}</span>` : ''}
                    </div>
                </div>
            `;
        }).join('');

        // 绑定点击事件
        placesList.querySelectorAll('.place-card').forEach(card => {
            card.addEventListener('click', () => {
                const index = parseInt(card.dataset.index);
                highlightPlace(index);
            });
        });
    }

    /**
     * 高亮某个地点
     */
    function highlightPlace(index) {
        // 更新卡片样式
        placesList.querySelectorAll('.place-card').forEach((card, i) => {
            card.classList.toggle('active', i === index);
        });

        // 在地图上显示
        const place = currentPlaces[index];
        if (place && place.latitude && place.longitude) {
            const marker = mapManager.markers[index];
            if (marker) {
                mapManager.showInfoWindow(place, marker);
            }
        }
    }

    /**
     * 渲染行程时间轴
     */
    function renderTimeline(plan) {
        if (!plan || !plan.stops || plan.stops.length === 0) {
            timelineSection.style.display = 'none';
            return;
        }

        currentPlan = plan;
        timelineSection.style.display = 'block';

        timeline.innerHTML = plan.stops.map((stop, index) => {
            const place = stop.place || {};
            const isFood = place.category === '美食';

            return `
                <div class="timeline-item ${isFood ? 'food' : ''}">
                    <div class="timeline-dot"></div>
                    <div class="timeline-time">${stop.arrival_time}</div>
                    <div class="timeline-content">
                        <div class="timeline-title">${place.name || '未知地点'}</div>
                        ${stop.activity ? `<div class="timeline-desc">${stop.activity}</div>` : ''}
                        <div class="timeline-desc">⏱️ 停留 ${stop.stay_duration} 分钟</div>
                        ${stop.distance_to_next ? `
                            <div class="timeline-transport">
                                🚶 ${stop.transport_to_next || '步行'} 
                                约 ${(stop.distance_to_next / 1000).toFixed(1)}公里, 
                                ${stop.duration_to_next} 分钟
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');

        // 渲染总结
        tripSummary.innerHTML = `
            <div class="trip-summary-stats">
                <div class="trip-summary-stat">
                    <span>📍</span>
                    <span>${plan.stops.length} 个站点</span>
                </div>
                <div class="trip-summary-stat">
                    <span>📏</span>
                    <span>${(plan.total_distance / 1000).toFixed(1)} 公里</span>
                </div>
                <div class="trip-summary-stat">
                    <span>⏱️</span>
                    <span>${Math.floor(plan.total_duration / 60)}小时${plan.total_duration % 60}分钟</span>
                </div>
            </div>
            ${plan.tips ? `<div class="trip-summary-tips">"${plan.tips}"</div>` : ''}
        `;
    }

    /**
     * 格式化数字
     */
    function formatNumber(num) {
        if (num >= 10000) {
            return (num / 10000).toFixed(1) + '万';
        }
        if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'k';
        }
        return num.toString();
    }

    /**
     * 处理表单提交
     */
    async function handleSubmit(e) {
        e.preventDefault();

        if (isLoading) return;

        const location = locationInput.value.trim();
        const startTime = startTimeInput.value;

        if (!location) {
            alert('请输入目的地');
            return;
        }

        // 重置UI
        setLoading(true);
        clearStatusMessages();
        placesSection.style.display = 'none';
        timelineSection.style.display = 'none';
        mapManager.clear();

        // 初始化地图
        mapManager.init();
        await mapManager.setCity(location.substring(0, 2));

        addStatusMessage(`🚀 开始为"${location}"规划一日行程...`);

        try {
            // 调用API
            const result = await api.createPlan(location, startTime);

            // 显示处理消息
            if (result.messages) {
                result.messages.forEach(msg => {
                    addStatusMessage(msg);
                });
            }

            if (result.success) {
                // 渲染地点列表
                if (result.places && result.places.length > 0) {
                    renderPlaces(result.places);
                    mapManager.addMarkers(result.places);
                }

                // 渲染行程
                if (result.plan) {
                    renderTimeline(result.plan);
                    mapManager.drawRoute(result.plan.stops);
                }

                addStatusMessage('✅ 行程规划完成！');
            } else {
                addStatusMessage(`❌ 规划失败: ${result.error || '未知错误'}`);
            }

        } catch (error) {
            addStatusMessage(`❌ 请求失败: ${error.message}`);
            console.error('规划失败:', error);
        } finally {
            setLoading(false);
        }
    }

    // 绑定事件
    searchForm.addEventListener('submit', handleSubmit);

    // 检查API可用性
    api.healthCheck().then(ok => {
        if (!ok) {
            addStatusMessage('⚠️ 后端服务未启动，请先运行 uvicorn main:app --reload');
        }
    });
});
