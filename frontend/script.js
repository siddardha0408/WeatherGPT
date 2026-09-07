/**
 * WeatherGPT — Frontend Application Controller
 * Handles automatic GPS geolocation, conversational NLP queries,
 * Web Speech voice input/output, dynamic metric cards, risk matrix,
 * agricultural advisories, IMD alerts, and Chart.js forecast/climate graphs.
 */

// API Configuration
const API_BASE = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? (window.location.port === "8000" ? window.location.origin : "http://127.0.0.1:8000")
    : window.location.origin;

// State Management
let currentLocation = {
    latitude: 16.3067,
    longitude: 80.4365,
    city: "Guntur",
    isDetected: false
};
let selectedLocation = null;
let currentSpeechLocale = "en-IN";
let recognition = null;
let isRecording = false;
let hourlyChartInstance = null;
let climateChartInstance = null;

// DOM Elements
const queryInput = document.getElementById("queryInput");
const queryForm = document.getElementById("queryForm");
const askBtn = document.getElementById("askBtn");
const micBtn = document.getElementById("micBtn");
const micIcon = document.getElementById("micIcon");
const useLocationBtn = document.getElementById("useLocationBtn");
const loadingIndicator = document.getElementById("loadingIndicator");
const loadingMessage = document.getElementById("loadingMessage");
const errorBanner = document.getElementById("errorBanner");
const errorMessage = document.getElementById("errorMessage");
const dismissErrorBtn = document.getElementById("dismissErrorBtn");

const headerLocationName = document.getElementById("headerLocationName");
const displayCityName = document.getElementById("displayCityName");
const displayDateTime = document.getElementById("displayDateTime");
const currentTemp = document.getElementById("currentTemp");
const currentFeelsLike = document.getElementById("currentFeelsLike");
const currentCondition = document.getElementById("currentCondition");
const weatherConditionIcon = document.getElementById("weatherConditionIcon");
const todayHighLow = document.getElementById("todayHighLow");
const rainChanceTag = document.getElementById("rainChanceTag");
const windTag = document.getElementById("windTag");

// Metric Card Elements
const mTemp = document.getElementById("mTemp");
const mFeels = document.getElementById("mFeels");
const mHumidity = document.getElementById("mHumidity");
const mRainProb = document.getElementById("mRainProb");
const mPrecip = document.getElementById("mPrecip");
const mWind = document.getElementById("mWind");
const mUV = document.getElementById("mUV");
const mVis = document.getElementById("mVis");
const mPressure = document.getElementById("mPressure");
const mCloud = document.getElementById("mCloud");

// Intelligence & Risk Elements
const overallRiskBadge = document.getElementById("overallRiskBadge");
const heatRiskBadge = document.getElementById("heatRiskBadge");
const rainRiskBadge = document.getElementById("rainRiskBadge");
const windRiskBadge = document.getElementById("windRiskBadge");
const uvRiskBadge = document.getElementById("uvRiskBadge");
const visRiskBadge = document.getElementById("visRiskBadge");
const advisoriesList = document.getElementById("advisoriesList");

// Agriculture Elements
const agriSuitabilityBadge = document.getElementById("agriSuitabilityBadge");
const agriSummaryText = document.getElementById("agriSummaryText");
const agriFactors = document.getElementById("agriFactors");
const agriRec = document.getElementById("agriRec");

// IMD Elements
const imdWarningSection = document.getElementById("imdWarningSection");
const imdBadge = document.getElementById("imdBadge");
const imdActionAdvice = document.getElementById("imdActionAdvice");
const imdEventsContainer = document.getElementById("imdEventsContainer");

// AI & Speech Elements
const aiAnswerContent = document.getElementById("aiAnswerContent");
const readAnswerBtn = document.getElementById("readAnswerBtn");
const stopVoiceBtn = document.getElementById("stopVoiceBtn");

// Forecast & Climate Elements
const dailyDeck = document.getElementById("dailyDeck");
const climateYearRange = document.getElementById("climateYearRange");
const loadClimateBtn = document.getElementById("loadClimateBtn");
const climateSummaryText = document.getElementById("climateSummaryText");


// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
    initApp();
    setupEventListeners();
    setupSpeechRecognition();
});


/**
 * Initial Application Bootstrap
 */
function initApp() {
    updateDateTimeDisplay();
    setInterval(updateDateTimeDisplay, 60000);

    // Automatic Browser Geolocation on load
    detectBrowserLocation();
}


/**
 * Setup All UI Event Listeners
 */
function setupEventListeners() {
    queryForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = queryInput.value.trim();
        if (text) {
            handleConversationalQuery(text);
        }
    });

    useLocationBtn.addEventListener("click", () => {
        detectBrowserLocation(true);
    });

    micBtn.addEventListener("click", toggleVoiceRecording);

    readAnswerBtn.addEventListener("click", speakAIResponse);
    stopVoiceBtn.addEventListener("click", stopSpeech);

    dismissErrorBtn.addEventListener("click", () => {
        errorBanner.classList.add("hidden");
    });

    loadClimateBtn.addEventListener("click", () => {
        const val = climateYearRange.value.split("-");
        const sYr = parseInt(val[0], 10);
        const eYr = parseInt(val[1], 10);
        fetchClimateTrends(sYr, eYr);
    });

    // Quick Prompt Chips
    document.querySelectorAll(".chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const query = chip.getAttribute("data-query");
            if (query) {
                queryInput.value = query;
                handleConversationalQuery(query);
            }
        });
    });
}


/**
 * Automatic Geolocation Detection
 */
function detectBrowserLocation(forceRefresh = false) {
    if (!navigator.geolocation) {
        showError("Geolocation is not supported by your browser.", "Using default meteorological region (Guntur, India).");
        fetchDefaultWeather();
        return;
    }

    headerLocationName.textContent = "Requesting GPS location...";
    showLoading("Locating your coordinates via Browser GPS...");

    navigator.geolocation.getCurrentPosition(
        async (position) => {
            currentLocation.latitude = position.coords.latitude;
            currentLocation.longitude = position.coords.longitude;
            currentLocation.isDetected = true;
            selectedLocation = null;

            await loadWeatherForCoordinates(currentLocation.latitude, currentLocation.longitude);
            hideLoading();
        },
        (error) => {
            console.warn("Geolocation denied or unavailable:", error.message);
            headerLocationName.textContent = "Guntur, Andhra Pradesh";
            hideLoading();
            if (forceRefresh) {
                showError("Location Permission Denied", "Please type a city name or enable location permissions in your browser settings.");
            }
            fetchDefaultWeather();
        },
        { timeout: 8000, enableHighAccuracy: false }
    );
}


async function fetchDefaultWeather() {
    await loadWeatherForCoordinates(currentLocation.latitude, currentLocation.longitude, "Guntur");
}


/**
 * Load Standard Weather Payload for Lat/Lon
 */
async function loadWeatherForCoordinates(lat, lon, cityName = null) {
    showLoading("Retrieving meteorological conditions & forecast...");
    try {
        let url = `${API_BASE}/weather?latitude=${lat}&longitude=${lon}`;
        if (cityName) url += `&city=${encodeURIComponent(cityName)}`;

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Weather service returned status ${response.status}`);
        }

        const data = await response.json();
        renderWeatherDashboard(data);
        
        // Fetch default agriculture & IMD status
        fetchAgricultureAdvisory(lat, lon, data.location?.city || cityName);
        fetchImdAlerts(lat, lon, data.location?.city || cityName);

        // Populate initial conversational summary
        if (data.current) {
            aiAnswerContent.textContent = `Current weather in ${data.location?.city || 'your area'} is ${data.current.temperature}°C with ${data.current.condition.toLowerCase()} skies and ${data.current.humidity}% humidity. Overall weather risk is ${data.weather_intelligence?.overall_risk?.level || 'Low'}.`;
        }

    } catch (err) {
        console.error("Error loading weather data:", err);
        showError("Weather Data Error", "Unable to contact meteorological servers. Please check your network connection.");
    } finally {
        hideLoading();
    }
}


/**
 * Main Conversational Ask Pipeline Handler
 */
async function handleConversationalQuery(questionText) {
    stopSpeech(); // Immediately silence any playing audio
    showLoading("Analyzing question with WeatherGPT intelligence...");
    errorBanner.classList.add("hidden");

    try {
        const payload = {
            question: questionText,
            latitude: currentLocation.latitude,
            longitude: currentLocation.longitude,
            city: selectedLocation || currentLocation.city,
            language: "en"
        };

        const response = await fetch(`${API_BASE}/ask`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`Server returned HTTP ${response.status}`);
        }

        const result = await response.json();

        // 1. Display AI Conversational Answer
        if (result.answer) {
            aiAnswerContent.innerHTML = formatMarkdown(result.answer);
            currentSpeechLocale = result.speech_locale || "en-IN";
        }

        // 2. If non-weather question
        if (result.is_weather_related === false) {
            hideLoading();
            return;
        }

        // 3. Update Dashboard if weather payload present
        if (result.weather && Object.keys(result.weather).length > 0) {
            const combinedData = {
                location: result.location,
                current: result.weather,
                weather_intelligence: result.weather_intelligence,
                daily: result.daily_forecast || [],
                hourly: result.hourly_forecast || []
            };
            renderWeatherDashboard(combinedData);
        }

        // 4. Update Agriculture Advisory if present
        if (result.agriculture_advisory) {
            renderAgricultureCard(result.agriculture_advisory);
        }

        // 5. Update IMD Alerts if present
        if (result.official_warning) {
            renderImdAlerts(result.official_warning);
        }

        // 6. Update Climate / History if present
        if (result.climate_trend) {
            renderClimateTrend(result.climate_trend);
        }

        // 7. Update current selected city tracker
        if (result.location && result.location.city) {
            selectedLocation = result.location.city;
            headerLocationName.textContent = result.location.city;
        }

        // 8. Dynamic Parameter Focus / Card Emphasis
        if (result.understanding && result.understanding.parameter) {
            highlightMetricCard(result.understanding.parameter);
        }

    } catch (err) {
        console.error("Conversational query failure:", err);
        showError("Intelligence Service Unavailable", "Unable to complete AI query analysis right now. Please try again.");
    } finally {
        hideLoading();
    }
}


/**
 * Render Complete Weather Dashboard
 */
function renderWeatherDashboard(data) {
    if (!data) return;

    const loc = data.location || {};
    const cur = data.current || {};
    const intel = data.weather_intelligence || {};
    const daily = data.daily || [];
    const hourly = data.hourly || [];

    // Header & Primary Card
    const cityLabel = loc.city || "Current Location";
    headerLocationName.textContent = cityLabel;
    displayCityName.textContent = cityLabel;

    currentTemp.textContent = cur.temperature !== undefined ? Math.round(cur.temperature) : "--";
    currentFeelsLike.textContent = cur.feels_like !== undefined ? `${Math.round(cur.feels_like)}°C` : "--°C";
    currentCondition.textContent = cur.condition || "Clear";
    weatherConditionIcon.textContent = cur.icon || "🌤️";

    // High / Low & Tags
    if (daily.length > 0) {
        const today = daily[0];
        todayHighLow.textContent = `High: ${Math.round(today.temp_max)}°C / Low: ${Math.round(today.temp_min)}°C`;
        rainChanceTag.textContent = `🌧️ Rain: ${today.precipitation_probability}%`;
    }
    windTag.textContent = `💨 Wind: ${cur.wind_speed || 0} km/h`;

    // 10 Metric Cards
    mTemp.textContent = `${cur.temperature || 0}°C`;
    mFeels.textContent = `${cur.feels_like || 0}°C`;
    mHumidity.textContent = `${cur.humidity || 0}%`;
    mRainProb.textContent = `${cur.precipitation_probability || 0}%`;
    mPrecip.textContent = `${cur.precipitation || 0} mm`;
    mWind.textContent = `${cur.wind_speed || 0} km/h`;
    mUV.textContent = `${cur.uv_index || 0}`;
    mVis.textContent = `${cur.visibility || 10} km`;
    mPressure.textContent = `${cur.pressure || 1013} hPa`;
    mCloud.textContent = `${cur.cloud_cover || 0}%`;

    // Risk Matrix
    if (intel.overall_risk) {
        overallRiskBadge.textContent = intel.overall_risk.badge || intel.overall_risk.level;
    }
    updateRiskBadge(heatRiskBadge, intel.heat_risk?.level || "Low");
    updateRiskBadge(rainRiskBadge, intel.rain_risk?.level || "Very Low");
    updateRiskBadge(windRiskBadge, intel.wind_risk?.level || "Low");
    updateRiskBadge(uvRiskBadge, intel.uv_risk?.level || "Moderate");
    updateRiskBadge(visRiskBadge, intel.visibility_risk?.level || "Good");

    // Advisories
    if (intel.advisories && intel.advisories.length > 0) {
        advisoriesList.innerHTML = intel.advisories.map(adv => `<li>${adv}</li>`).join("");
    }

    // 7-Day Forecast Deck
    render7DayForecast(daily);

    // 24-Hour Hourly Chart
    renderHourlyChart(hourly);
}


/**
 * Render 7-Day Daily Forecast Deck
 */
function render7DayForecast(dailyList) {
    if (!dailyList || dailyList.length === 0) return;

    const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

    dailyDeck.innerHTML = dailyList.map((day, idx) => {
        let label = "Day";
        if (idx === 0) label = "Today";
        else if (idx === 1) label = "Tomorrow";
        else if (day.date) {
            const d = new Date(day.date);
            label = dayNames[d.getDay()] || day.date;
        }

        return `
            <div class="daily-card ${idx === 0 ? 'active' : ''}">
                <div class="day-title">${label}</div>
                <div class="day-date">${day.date ? day.date.slice(5) : ''}</div>
                <div class="day-icon">${day.icon || '🌤️'}</div>
                <div class="day-condition">${day.condition || 'Clear'}</div>
                <div class="day-temps">
                    <span class="day-max">${Math.round(day.temp_max)}°</span> / 
                    <span class="day-min">${Math.round(day.temp_min)}°</span>
                </div>
                <div class="day-rain">🌧️ ${day.precipitation_probability}%</div>
            </div>
        `;
    }).join("");
}


/**
 * Render 24-Hour Forecast Chart using Chart.js
 */
function renderHourlyChart(hourlyList) {
    const ctx = document.getElementById("hourlyChart");
    if (!ctx || !hourlyList || hourlyList.length === 0) return;

    const labels = hourlyList.map(item => {
        if (!item.time) return "";
        const parts = item.time.split("T");
        return parts.length > 1 ? parts[1].slice(0, 5) : item.time;
    });

    const temps = hourlyList.map(item => item.temperature);
    const rainProbs = hourlyList.map(item => item.precipitation_probability);

    if (hourlyChartInstance) {
        hourlyChartInstance.destroy();
    }

    hourlyChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Temperature (°C)',
                    data: temps,
                    borderColor: '#0284c7',
                    backgroundColor: 'rgba(2, 132, 199, 0.1)',
                    fill: true,
                    tension: 0.35,
                    yAxisID: 'y'
                },
                {
                    label: 'Rain Chance (%)',
                    data: rainProbs,
                    type: 'bar',
                    backgroundColor: 'rgba(6, 182, 212, 0.45)',
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: { grid: { display: false } },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: { display: true, text: '°C' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    min: 0,
                    max: 100,
                    grid: { drawOnChartArea: false },
                    title: { display: true, text: 'Rain %' }
                }
            },
            plugins: {
                legend: { position: 'top', labels: { boxWidth: 12 } }
            }
        }
    });
}


/**
 * Fetch & Render Agriculture Advisory
 */
async function fetchAgricultureAdvisory(lat, lon, cityName) {
    try {
        const res = await fetch(`${API_BASE}/agriculture-advisory?latitude=${lat}&longitude=${lon}&city=${encodeURIComponent(cityName || 'Guntur')}`);
        if (res.ok) {
            const data = await res.json();
            renderAgricultureCard(data);
        }
    } catch (e) {
        console.warn("Agriculture advisory fetch:", e);
    }
}


function renderAgricultureCard(agri) {
    if (!agri) return;
    const spray = agri.spraying_suitability || {};
    
    agriSuitabilityBadge.textContent = spray.badge || spray.suitability || "Suitable";
    agriSummaryText.textContent = spray.summary || "Conditions analyzed for agricultural operations.";
    agriRec.textContent = spray.recommendation || "Early morning window recommended.";

    if (spray.favorable_factors && spray.favorable_factors.length > 0) {
        agriFactors.innerHTML = spray.favorable_factors.map(f => `<div class="agri-pill favorable">✅ ${f}</div>`).join("");
    } else if (spray.risk_factors && spray.risk_factors.length > 0) {
        agriFactors.innerHTML = spray.risk_factors.map(r => `<div class="agri-pill" style="background:#fee2e2;color:#991b1b;border-color:#fecaca;">⚠️ ${r}</div>`).join("");
    }
}


/**
 * Fetch & Render IMD Official Alerts
 */
async function fetchImdAlerts(lat, lon, cityName) {
    try {
        const res = await fetch(`${API_BASE}/imd-warning?latitude=${lat}&longitude=${lon}&city=${encodeURIComponent(cityName || 'Guntur')}`);
        if (res.ok) {
            const data = await res.json();
            renderImdAlerts(data);
        }
    } catch (e) {
        console.warn("IMD alert fetch:", e);
    }
}


function renderImdAlerts(imd) {
    if (!imd || !imd.official_warning_available) {
        imdWarningSection.classList.add("hidden");
        return;
    }

    if (imd.official_warning || imd.color_code < 4) {
        imdWarningSection.classList.remove("hidden");
        imdBadge.textContent = imd.badge || imd.level || "🟡 Warning";
        imdActionAdvice.textContent = imd.action_advice || "Official meteorological bulletin issued.";

        if (imd.events && imd.events.length > 0) {
            imdEventsContainer.innerHTML = imd.events.map(ev => `
                <div class="imd-event-item">⚡ <strong>${ev.event}</strong>: ${ev.description} (Valid: ${ev.valid_until})</div>
            `).join("");
        } else {
            imdEventsContainer.innerHTML = "";
        }
    } else {
        imdWarningSection.classList.add("hidden");
    }
}


/**
 * Fetch & Render Multi-Year Climate Trends
 */
async function fetchClimateTrends(sYear = 2021, eYear = 2025) {
    showLoading(`Computing ${sYear}–${eYear} multi-year climate tendencies...`);
    try {
        const lat = currentLocation.latitude;
        const lon = currentLocation.longitude;
        const city = selectedLocation || currentLocation.city || "Guntur";

        const res = await fetch(`${API_BASE}/climate-trend?latitude=${lat}&longitude=${lon}&city=${encodeURIComponent(city)}&start_year=${sYear}&end_year=${eYear}`);
        if (!res.ok) throw new Error("Climate trend endpoint error");

        const data = await res.json();
        renderClimateTrend(data);

    } catch (err) {
        console.error("Climate trend fetch error:", err);
        showError("Climate Trend Error", "Unable to calculate multi-year climate dataset.");
    } finally {
        hideLoading();
    }
}


function renderClimateTrend(trendData) {
    if (!trendData || !trendData.yearly_records) return;

    const rfTrend = trendData.rainfall_trend || {};
    const tmpTrend = trendData.temperature_trend || {};

    climateSummaryText.innerHTML = `
        <p><strong>Precipitation Trend:</strong> Annual rainfall is exhibiting a <em>${rfTrend.trend || 'stable'}</em> tendency (${rfTrend.percentage_change >= 0 ? '+' : ''}${rfTrend.percentage_change}% change, slope: ${rfTrend.slope_mm_per_year} mm/yr).</p>
        <p><strong>Temperature Trend:</strong> Average temperature exhibits a <em>${tmpTrend.trend || 'stable'}</em> slope (${tmpTrend.slope_c_per_year >= 0 ? '+' : ''}${tmpTrend.slope_c_per_year} °C/yr).</p>
        <p style="font-size:0.8rem;color:var(--text-muted);margin-top:0.4rem;">${trendData.scientific_disclaimer || ''}</p>
    `;

    const ctx = document.getElementById("climateChart");
    if (!ctx) return;

    const years = trendData.yearly_records.map(r => r.year);
    const rains = trendData.yearly_records.map(r => r.total_rainfall_mm);
    const temps = trendData.yearly_records.map(r => r.avg_temperature_c);

    if (climateChartInstance) {
        climateChartInstance.destroy();
    }

    climateChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: years,
            datasets: [
                {
                    label: 'Annual Rainfall (mm)',
                    data: rains,
                    backgroundColor: 'rgba(2, 132, 199, 0.65)',
                    borderColor: '#0284c7',
                    borderWidth: 1,
                    yAxisID: 'y'
                },
                {
                    label: 'Avg Temperature (°C)',
                    data: temps,
                    type: 'line',
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.2)',
                    tension: 0.3,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    type: 'linear',
                    position: 'left',
                    title: { display: true, text: 'Rainfall (mm)' }
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    title: { display: true, text: 'Avg Temp (°C)' },
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });
}


/**
 * Web Speech API: Voice Input
 */
function setupSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        micBtn.style.opacity = "0.5";
        micBtn.title = "Voice recognition not supported in this browser";
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-IN";

    recognition.onstart = () => {
        isRecording = true;
        micBtn.classList.add("recording");
        micIcon.textContent = "🛑";
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        queryInput.value = transcript;
        handleConversationalQuery(transcript);
    };

    recognition.onerror = (event) => {
        console.warn("Speech recognition error:", event.error);
        stopVoiceRecording();
    };

    recognition.onend = () => {
        stopVoiceRecording();
    };
}

function toggleVoiceRecording() {
    if (!recognition) {
        alert("Voice recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.");
        return;
    }
    stopSpeech(); // Stop any active speaker output before listening
    if (isRecording) {
        recognition.stop();
    } else {
        recognition.start();
    }
}

function stopVoiceRecording() {
    isRecording = false;
    micBtn.classList.remove("recording");
    micIcon.textContent = "🎤";
}


let currentUtterance = null;

// Ensure voices are loaded in Chromium
if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = () => {
        // Voices refreshed
    };
}

/**
 * Web Speech API: Voice Output (SpeechSynthesis)
 */
function speakAIResponse() {
    if (!('speechSynthesis' in window)) {
        alert("Text-to-speech is not supported in this browser.");
        return;
    }

    // Immediately stop and clear any previous speech without delayed callbacks
    if (window.speechSynthesis.speaking || window.speechSynthesis.pending || window.speechSynthesis.paused) {
        if (currentUtterance) {
            currentUtterance.onstart = null;
            currentUtterance.onend = null;
            currentUtterance.onerror = null;
            currentUtterance = null;
        }
        window.speechSynthesis.cancel();
        if (window.speechSynthesis.paused) {
            window.speechSynthesis.resume();
        }
    }

    const rawText = aiAnswerContent.innerText || aiAnswerContent.textContent;
    if (!rawText || !rawText.trim()) return;

    // Clean text: strip emojis, markdown symbols, and extra whitespace
    const cleanText = rawText
        .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, '')
        .replace(/[*_#`~>]/g, '')
        .replace(/\s+/g, ' ')
        .trim();

    if (!cleanText) return;

    // Short tick ensures the browser speech engine has settled before speaking
    setTimeout(() => {
        try {
            const utterance = new SpeechSynthesisUtterance(cleanText);
            utterance.lang = currentSpeechLocale || "en-IN";
            utterance.rate = 0.95;
            utterance.pitch = 1.0;

            // Pick matching voice
            const voices = window.speechSynthesis.getVoices();
            if (voices && voices.length > 0) {
                const targetLang = (currentSpeechLocale || "en-IN").toLowerCase();
                const prefix = targetLang.slice(0, 2);
                const matchedVoice = voices.find(v => v.lang.toLowerCase() === targetLang) ||
                                     voices.find(v => v.lang.toLowerCase().startsWith(prefix)) ||
                                     voices.find(v => v.lang.toLowerCase().includes("in"));
                if (matchedVoice) {
                    utterance.voice = matchedVoice;
                }
            }

            utterance.onstart = () => {
                readAnswerBtn.classList.add("hidden");
                stopVoiceBtn.classList.remove("hidden");
            };

            utterance.onend = () => {
                currentUtterance = null;
                readAnswerBtn.classList.remove("hidden");
                stopVoiceBtn.classList.add("hidden");
            };

            utterance.onerror = (e) => {
                // 'interrupted' and 'canceled' are normal when user clicks stop or new query starts
                if (e.error !== 'interrupted' && e.error !== 'canceled') {
                    console.warn("Speech synthesis error:", e.error);
                }
                currentUtterance = null;
                readAnswerBtn.classList.remove("hidden");
                stopVoiceBtn.classList.add("hidden");
            };

            currentUtterance = utterance;
            window.speechSynthesis.speak(utterance);

        } catch (err) {
            console.error("Speech synthesis invocation failed:", err);
            readAnswerBtn.classList.remove("hidden");
            stopVoiceBtn.classList.add("hidden");
        }
    }, 25);
}

function stopSpeech() {
    if ('speechSynthesis' in window) {
        if (currentUtterance) {
            currentUtterance.onstart = null;
            currentUtterance.onend = null;
            currentUtterance.onerror = null;
            currentUtterance = null;
        }
        window.speechSynthesis.cancel();
        if (window.speechSynthesis.paused) {
            window.speechSynthesis.resume();
        }
    }
    readAnswerBtn.classList.remove("hidden");
    stopVoiceBtn.classList.add("hidden");
}

window.addEventListener("beforeunload", stopSpeech);
window.addEventListener("pagehide", stopSpeech);


/**
 * Helper Utilities
 */
function updateRiskBadge(badgeElem, level) {
    if (!badgeElem) return;
    badgeElem.textContent = level;
    badgeElem.className = `risk-badge ${level.replace(/\s+/g, '-')}`;
}

function highlightMetricCard(param) {
    const cardMap = {
        "temperature": "cardTemp",
        "apparent_temperature": "cardFeelsLike",
        "humidity": "cardHumidity",
        "rain_probability": "cardRainProb",
        "rainfall": "cardPrecipitation",
        "wind": "cardWind",
        "uv_index": "cardUV",
        "visibility": "cardVisibility",
        "surface_pressure": "cardPressure",
        "cloud_cover": "cardCloudCover"
    };

    const targetId = cardMap[param];
    if (targetId) {
        const card = document.getElementById(targetId);
        if (card) {
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            card.style.borderColor = '#0284c7';
            card.style.boxShadow = '0 0 12px rgba(2, 132, 199, 0.4)';
            setTimeout(() => {
                card.style.borderColor = '';
                card.style.boxShadow = '';
            }, 3000);
        }
    }
}

function formatMarkdown(text) {
    if (!text) return "";
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n\n/g, '<br><br>')
        .replace(/\n/g, '<br>');
}

function updateDateTimeDisplay() {
    const now = new Date();
    const options = { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    displayDateTime.textContent = now.toLocaleDateString('en-US', options);
}

function showLoading(msg) {
    loadingMessage.textContent = msg || "Processing meteorological request...";
    loadingIndicator.classList.remove("hidden");
}

function hideLoading() {
    loadingIndicator.classList.add("hidden");
}

function showError(title, msg) {
    document.getElementById("errorTitle").textContent = title || "Notice";
    errorMessage.textContent = msg || "An error occurred.";
    errorBanner.classList.remove("hidden");
}
