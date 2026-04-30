export function formatDate(dateObj) {
    if (!dateObj) return null;

    // Jika sudah string YYYY-MM-DD
    if (typeof dateObj === "string" && dateObj.length === 10) {
        return dateObj;
    }

    const d = new Date(dateObj);
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const year = d.getFullYear();

    return `${year}-${month}-${day}`;
}

export function formatDateId(dateObj) {
    if (!dateObj) return null;

    if (typeof dateObj === "string" && dateObj.length === 10) {
        return dateObj;
    }

    const d = new Date(dateObj);
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const year = d.getFullYear();

    return `${day}-${month}-${year}`;
}

export function formatDateTimeId(dateObj) {
    if (!dateObj) return null;

    if (typeof dateObj === "string" && dateObj.length === 10) {
        return dateObj;
    }

    const d = new Date(dateObj);
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const year = d.getFullYear();
    const hours = String(d.getHours()).padStart(2, "0");
    const minutes = String(d.getMinutes()).padStart(2, "0");
    const seconds = String(d.getSeconds()).padStart(2, "0");

    return `${day}-${month}-${year} ${hours}:${minutes}:${seconds}`;
}
export function formatCurrencyDigit(value) {
    if (!value) return "Rp 0";

    const num = Number(value);  

    return num.toLocaleString("id-ID", {
        style: "currency",
        currency: "IDR",
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });
}

export function formatNumber(value) {
    if (value == null) return 0;

    const num = Number(value); 

    return num.toLocaleString("id-ID", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });
}

export function toFormData(payload) {
    const formData = new FormData();
    Object.entries(payload).forEach(([key, value]) => {
        if (value === null || value === undefined) return;
        if (value instanceof File) {
            formData.append(key, value);
        }
        else if (typeof value === "object") {
            formData.append(key, JSON.stringify(value));
        }
        else {
            formData.append(key, value);
        }
    });

    return formData;
}

export function formatDatetoIsost(date) {
    return date.toISOString().split('T')[0];
}

export function debounce(fn, delay = 500) {
  let timeout
  return (...args) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => fn(...args), delay)
  }
}
