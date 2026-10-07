(() => {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ?? "";
  const balance = document.getElementById("balance");
  const transactionList = document.getElementById("transaction-list");
  const loanHistory = document.getElementById("loan-history");
  const syncStatus = document.getElementById("sync-status");
  let refreshing = false;

  const money = (amount) => Number(amount).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const dateLabel = (value) => {
    const parsed = new Date(value);
    return Number.isNaN(parsed.valueOf()) ? value : parsed.toLocaleString();
  };

  function renderTransactions(items) {
    transactionList.replaceChildren();
    if (!items.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.innerHTML = "<span>⌁</span><strong>No activity yet</strong><p>Demo transactions will show up here.</p>";
      transactionList.append(empty);
      return;
    }
    items.forEach((item) => {
      const incoming = ["deposit", "transfer_received"].includes(item.type);
      const row = document.createElement("div");
      row.className = "transaction-row";
      const mark = document.createElement("span");
      mark.className = `transaction-mark${incoming ? " positive" : ""}`;
      mark.textContent = incoming ? "↓" : "↑";
      const description = document.createElement("span");
      description.className = "transaction-description";
      const title = document.createElement("strong");
      title.textContent = item.description;
      const date = document.createElement("small");
      date.textContent = dateLabel(item.created_at);
      description.append(title, date);
      const amount = document.createElement("strong");
      amount.className = `transaction-amount${incoming ? " positive-text" : ""}`;
      amount.textContent = `${incoming ? "+" : "−"}₹${money(item.amount)}`;
      row.append(mark, description, amount);
      transactionList.append(row);
    });
  }

  function renderLoans(items) {
    loanHistory.replaceChildren();
    if (!items.length) {
      const empty = document.createElement("div");
      empty.className = "loan-history-empty";
      empty.textContent = "No demo requests yet.";
      loanHistory.append(empty);
      return;
    }
    items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "loan-history-row";
      const title = document.createElement("span");
      title.textContent = `${item.type[0].toUpperCase()}${item.type.slice(1)} · ₹${money(item.amount)}`;
      const status = document.createElement("small");
      status.textContent = item.status;
      row.append(title, status);
      loanHistory.append(row);
    });
  }

  async function refresh() {
    if (refreshing) return;
    refreshing = true;
    try {
      const response = await fetch("/api/activity", {
        headers: { Accept: "application/json", "X-CSRF-Token": csrfToken },
        credentials: "same-origin",
      });
      if (response.status === 401 || response.redirected) {
        window.location.assign("/login");
        return;
      }
      if (!response.ok) throw new Error(`Refresh failed (${response.status}).`);
      const data = await response.json();
      balance.textContent = money(data.account.balance);
      renderTransactions(data.transactions);
      renderLoans(data.applications);
      syncStatus.textContent = `Updated ${new Date().toLocaleTimeString()}.`;
    } catch (error) {
      syncStatus.textContent = "Could not refresh demo activity. Retrying shortly.";
      console.error(error);
    } finally {
      refreshing = false;
    }
  }

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
        button.textContent = "Copied";
        window.setTimeout(() => { button.textContent = "Copy"; }, 1400);
      } catch {
        button.textContent = "Copy unavailable";
        window.setTimeout(() => { button.textContent = "Copy"; }, 1600);
      }
    });
  });

  const loanType = document.getElementById("loan-type");
  const loanDetails = document.getElementById("loan-details");
  const loanLabel = document.getElementById("loan-details-label");
  const loanHint = document.getElementById("loan-hint");
  const loanHelp = {
    education: ["Student status and two proofs", "student, ID card, admission letter", "Separate student status and at least two proofs with commas."],
    gold: ["Gold and quantity in grams", "Gold, 12.5", "Enter Gold and a positive quantity in grams, separated by a comma."],
    secured: ["Collateral documents", "House Documents", "Use House Documents, Farm Documents, or Property Documents."],
  };
  loanType.addEventListener("change", () => {
    const [label, placeholder, hint] = loanHelp[loanType.value];
    loanLabel.firstChild.textContent = `${label} `;
    loanDetails.placeholder = placeholder;
    loanHint.textContent = hint;
  });

  window.setInterval(refresh, 10000);
})();
