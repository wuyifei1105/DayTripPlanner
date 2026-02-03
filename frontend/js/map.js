/**
 * 地图管理模块
 */

class MapManager {
    constructor(containerId) {
        this.containerId = containerId;
        this.map = null;
        this.markers = [];
        this.polyline = null;
        this.infoWindow = null;
    }

    /**
     * 初始化地图
     * @param {number[]} center - 中心点坐标 [lng, lat]
     * @param {number} zoom - 缩放级别
     */
    init(center = [120.15, 30.28], zoom = 13) {
        // 隐藏占位符
        const placeholder = document.querySelector('.map-placeholder');
        if (placeholder) {
            placeholder.style.display = 'none';
        }

        // 创建地图容器
        const container = document.getElementById(this.containerId);
        let mapDiv = container.querySelector('#map');
        if (!mapDiv) {
            mapDiv = document.createElement('div');
            mapDiv.id = 'map';
            container.appendChild(mapDiv);
        }

        // 初始化高德地图
        this.map = new AMap.Map('map', {
            zoom: zoom,
            center: center,
            viewMode: '2D',
            mapStyle: 'amap://styles/light', // 浅色主题
        });

        // 添加控件
        this.map.addControl(new AMap.Scale());
        this.map.addControl(new AMap.ToolBar({
            position: 'RT',
        }));

        // 信息窗体
        this.infoWindow = new AMap.InfoWindow({
            offset: new AMap.Pixel(0, -30),
        });
    }

    /**
     * 添加标记点
     * @param {object[]} places - 地点数组
     */
    addMarkers(places) {
        // 清除现有标记
        this.clearMarkers();

        const validPlaces = places.filter(p => p.latitude && p.longitude);

        validPlaces.forEach((place, index) => {
            const isFood = place.category === '美食';

            // 创建标记
            const marker = new AMap.Marker({
                position: [place.longitude, place.latitude],
                title: place.name,
                label: {
                    content: `<span class="marker-label">${index + 1}</span>`,
                    direction: 'center',
                },
            });

            // 自定义图标
            marker.setIcon(new AMap.Icon({
                size: new AMap.Size(36, 36),
                image: isFood
                    ? 'https://webapi.amap.com/theme/v1.3/markers/n/mid.png'
                    : 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png',
                imageSize: new AMap.Size(36, 36),
            }));

            // 绑定点击事件
            marker.on('click', () => {
                this.showInfoWindow(place, marker);
            });

            marker.setMap(this.map);
            this.markers.push(marker);
        });

        // 自适应视野
        if (this.markers.length > 0) {
            this.map.setFitView(this.markers, false, [50, 50, 50, 50]);
        }
    }

    /**
     * 显示信息窗体
     * @param {object} place - 地点信息
     * @param {AMap.Marker} marker - 标记点
     */
    showInfoWindow(place, marker) {
        const content = `
            <div class="info-window">
                <h3>${place.name}</h3>
                <p class="info-category">${place.category || '景点'}</p>
                ${place.rating ? `<p class="info-rating">⭐ ${place.rating}</p>` : ''}
                ${place.price_range ? `<p class="info-price">💰 ${place.price_range}</p>` : ''}
                ${place.address ? `<p class="info-address">📍 ${place.address}</p>` : ''}
            </div>
        `;

        this.infoWindow.setContent(content);
        this.infoWindow.open(this.map, marker.getPosition());
    }

    /**
     * 绘制行程路线
     * @param {object[]} stops - 行程站点
     */
    drawRoute(stops) {
        // 清除现有路线
        if (this.polyline) {
            this.map.remove(this.polyline);
        }

        const path = stops
            .filter(stop => stop.place?.latitude && stop.place?.longitude)
            .map(stop => [stop.place.longitude, stop.place.latitude]);

        if (path.length < 2) return;

        this.polyline = new AMap.Polyline({
            path: path,
            strokeColor: '#6366f1',
            strokeWeight: 4,
            strokeOpacity: 0.8,
            strokeStyle: 'solid',
            lineJoin: 'round',
            lineCap: 'round',
        });

        this.polyline.setMap(this.map);
    }

    /**
     * 清除所有标记
     */
    clearMarkers() {
        this.markers.forEach(marker => {
            this.map.remove(marker);
        });
        this.markers = [];
    }

    /**
     * 清除所有内容
     */
    clear() {
        this.clearMarkers();
        if (this.polyline) {
            this.map.remove(this.polyline);
            this.polyline = null;
        }
        this.infoWindow.close();
    }

    /**
     * 定位到城市
     * @param {string} city - 城市名称
     */
    async setCity(city) {
        return new Promise((resolve) => {
            AMap.plugin('AMap.Geocoder', () => {
                const geocoder = new AMap.Geocoder({
                    city: city,
                });

                geocoder.getLocation(city, (status, result) => {
                    if (status === 'complete' && result.geocodes.length) {
                        const location = result.geocodes[0].location;
                        this.map.setCenter([location.lng, location.lat]);
                        resolve(true);
                    } else {
                        resolve(false);
                    }
                });
            });
        });
    }
}

// 全局实例
const mapManager = new MapManager('mapContainer');
