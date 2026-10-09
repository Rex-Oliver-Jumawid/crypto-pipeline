
const market = {
    "BTC-USD": [],
    "ETH-USD": [],
};

const assets = {
    "BTC-USD": {
        name: "Bitcoin",
        prefix: "btc",
        color: "#f5a623",
    },
    "ETH-USD": {
        name: "Ethereum",
        prefix: "eth",
        color: "#829bff",
    },
};

let selectedAsset = "BTC-USD";
let fetching = false;

const $ = (id) => document.getElementById(id);

function money(value) {
    if (value == null || !Number.isFinite(Number(value))) {
        return "--";
    }

    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(Number(value));
}

function number(value) {
    if (value == null || !Number.isFinite(Number(value))) {
        return "--";
    }

    return new Intl.NumberFormat("en-US", {
        maximumFractionDigits: 2,
    }).format(Number(value));
}

function change(value) {
    if (value == null || !Number.isFinite(Number(value))) {
        return "--";
    }

    const n = Number(value);

    return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

function utcTime(value) {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "--";
    }

    return date.toISOString()
        .replace("T", " ")
        .slice(0, 19) + " UTC";
}

function setStatus(message, type = "") {
    const status = $("connection-status");
    status.textContent = message;
    status.className = `status ${type}`;
}

function updateCards() {
    for (const [symbol, asset] of Object.entries(assets)) {
        const latest = market[symbol][0];

        $(`${asset.prefix}-price`).textContent =
            latest ? money(latest.price_usd) : "--";

        const indicator = $(`${asset.prefix}-change`);

        indicator.textContent = latest
            ? change(latest.price_change_pct_24h)
            : "--";

        indicator.className = "";

        if (latest && latest.price_change_pct_24h != null) {
            indicator.classList.add(
                Number(latest.price_change_pct_24h) >= 0
                    ? "positive"
                    : "negative"
            );
        }
    }
}

const SVG_NS = "http://www.w3.org/2000/svg";

function svgElement(tag, attributes, text) {
    const element = document.createElementNS(SVG_NS, tag);

    for (const [key, value] of Object.entries(attributes)) {
        element.setAttribute(key, String(value));
    }

    if (text !== undefined) {
        element.textContent = text;
    }

    return element;
}

function drawChart(records) {
    const svg = $("price-chart");
    svg.replaceChildren();

    const prices = records
        .filter((record) =>
            record.price_usd != null &&
            Number.isFinite(Number(record.price_usd))
        )
        .slice()
        .reverse();

    if (!prices.length) {
        svg.appendChild(svgElement("text", {
            x: 450,
            y: 150,
            fill: "#8b98b2",
            "text-anchor": "middle",
            "font-size": 16,
        }, "No market records available"));
        return;
    }

    const width = 900;
    const height = 300;
    const left = 88;
    const right = 20;
    const top = 20;
    const bottom = 45;

    const chartWidth = width - left - right;
    const chartHeight = height - top - bottom;

    const values = prices.map(
        (record) => Number(record.price_usd)
    );

    const lowest = Math.min(...values);
    const highest = Math.max(...values);

    const padding = Math.max(
        (highest - lowest) * 0.15,
        highest * 0.0001,
        0.01
    );

    const min = lowest - padding;
    const max = highest + padding;

    const x = (i) =>
        left + (i / Math.max(values.length - 1, 1)) * chartWidth;

    const y = (value) =>
        top + ((max - value) / (max - min)) * chartHeight;

    for (let i = 0; i <= 4; i++) {
        const value = max - ((max - min) * i / 4);
        const yy = y(value);

        svg.appendChild(svgElement("line", {
            x1: left,
            x2: width - right,
            y1: yy,
            y2: yy,
            stroke: "#2b3650",
            "stroke-dasharray": "4 5",
        }));

        svg.appendChild(svgElement("text", {
            x: left - 12,
            y: yy + 4,
            fill: "#8b98b2",
            "text-anchor": "end",
            "font-size": 12,
        }, money(value)));
    }

    const points = values.map(
        (value, i) => `${x(i)},${y(value)}`
    );

    const linePath = points
        .map((point, i) => `${i === 0 ? "M" : "L"} ${point}`)
        .join(" ");

    const areaPath = [
        linePath,
        `L ${x(values.length - 1)} ${height - bottom}`,
        `L ${x(0)} ${height - bottom}`,
        "Z",
    ].join(" ");

    const color = assets[selectedAsset].color;

    svg.appendChild(svgElement("path", {
        d: areaPath,
        fill: color,
        opacity: 0.09,
    }));

    svg.appendChild(svgElement("path", {
        d: linePath,
        fill: "none",
        stroke: color,
        "stroke-width": 3,
        "stroke-linejoin": "round",
        "stroke-linecap": "round",
    }));

    svg.appendChild(svgElement("circle", {
        cx: x(values.length - 1),
        cy: y(values[values.length - 1]),
        r: 5,
        fill: color,
        stroke: "#151c30",
        "stroke-width": 3,
    }));

    const first = prices[0];
    const last = prices[prices.length - 1];

    svg.appendChild(svgElement("text", {
        x: left,
        y: height - 13,
        fill: "#8b98b2",
        "font-size": 12,
    }, utcTime(first.event_time).slice(11)));

    svg.appendChild(svgElement("text", {
        x: width - right,
        y: height - 13,
        fill: "#8b98b2",
        "font-size": 12,
        "text-anchor": "end",
    }, utcTime(last.event_time).slice(11)));
}

function updateTable(records) {
    const table = $("market-table");
    table.replaceChildren();

    if (!records.length) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 4;
        cell.textContent = "No market records available.";

        row.appendChild(cell);
        table.appendChild(row);
        return;
    }

    for (const record of records.slice(0, 15)) {
        const row = document.createElement("tr");

        const columns = [
            utcTime(record.event_time),
            money(record.price_usd),
            change(record.price_change_pct_24h),
            number(record.volume_24h),
        ];

        columns.forEach((value, index) => {
            const cell = document.createElement("td");
            cell.textContent = value;

            if (index === 2 &&
                record.price_change_pct_24h != null) {
                cell.className =
                    Number(record.price_change_pct_24h) >= 0
                        ? "positive"
                        : "negative";
            }

            row.appendChild(cell);
        });

        table.appendChild(row);
    }
}

function render() {
    updateCards();

    const records = market[selectedAsset];
    const asset = assets[selectedAsset];
    const latest = records[0];

    $("chart-title").textContent =
        `${asset.name} Price History`;

    $("table-title").textContent =
        `${asset.name} Market Records`;

    $("high-price").textContent = latest
        ? money(latest.high_24h_usd) : "--";

    $("low-price").textContent = latest
        ? money(latest.low_24h_usd) : "--";

    $("market-volume").textContent = latest
        ? number(latest.volume_24h) : "--";

    document.querySelectorAll(".coin-card").forEach(
        (card) => {
            const active =
                card.dataset.symbol === selectedAsset;

            card.classList.toggle("selected", active);
            card.setAttribute("aria-pressed", String(active));
        }
    );

    drawChart(records);
    updateTable(records);
}

async function refreshMarket() {
    if (fetching) return;

    fetching = true;

    try {
        const response = await fetch("/api/prices", {
            cache: "no-store",
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        for (const symbol of Object.keys(market)) {
            market[symbol] = Array.isArray(data[symbol])
                ? data[symbol]
                : [];
        }

        render();

        const records = Object.values(market).flat();

        if (!records.length) {
            setStatus("Waiting for records");
            $("last-event").textContent =
                "No stored market records yet";
            return;
        }

        const latestEvent = Math.max(
            ...records.map((record) =>
                new Date(record.event_time).getTime()
            ).filter(Number.isFinite)
        );

        const age = Date.now() - latestEvent;

        $("last-event").textContent =
            `Latest market event: ${
                utcTime(new Date(latestEvent))
            }`;

        if (age >= 0 && age <= 120000) {
            setStatus("Live data", "live");
        } else {
            setStatus("Stored data (not recent)");
        }
    } catch (error) {
        console.error("Dashboard refresh failed:", error);
        setStatus("API unavailable", "error");
    } finally {
        fetching = false;
    }
}

document.querySelectorAll(".coin-card").forEach(
    (card) => {
        card.addEventListener("click", () => {
            selectedAsset = card.dataset.symbol;
            render();
        });
    }
);

render();
refreshMarket();
setInterval(refreshMarket, 5000);

