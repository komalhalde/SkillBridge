// ==========================================
// SkillBridge - Admin JavaScript
// ==========================================


// ---------- Confirm Delete ----------

function confirmDelete(message = "Are you sure you want to delete this item?") {
    return confirm(message);
}


// ---------- Select All Checkboxes ----------

function toggleSelectAll(source) {

    const checkboxes =
        document.querySelectorAll(
            'input[type="checkbox"].row-checkbox'
        );

    checkboxes.forEach(function (checkbox) {
        checkbox.checked = source.checked;
    });
}


// ---------- Table Search ----------

function searchTable(inputId, tableId) {

    const input =
        document.getElementById(inputId);

    const table =
        document.getElementById(tableId);

    if (!input || !table) {
        return;
    }

    const filter =
        input.value.toLowerCase();

    const rows =
        table.getElementsByTagName("tbody")[0]
             ?.getElementsByTagName("tr");

    if (!rows) {
        return;
    }

    for (let i = 0; i < rows.length; i++) {

        const text =
            rows[i].textContent.toLowerCase();

        rows[i].style.display =
            text.includes(filter) ? "" : "none";
    }
}


// ---------- Auto Hide Alerts ----------

document.addEventListener("DOMContentLoaded", function () {

    const alerts =
        document.querySelectorAll(".alert");

    alerts.forEach(function (alert) {

        // Only auto-hide alerts marked with data-auto-hide
        if (alert.dataset.autoHide === "true") {

            setTimeout(function () {

                alert.style.transition =
                    "opacity 0.5s ease";

                alert.style.opacity = "0";

                setTimeout(function () {
                    alert.remove();
                }, 500);

            }, 4000);
        }

    });

});


// ---------- Form Submit Loading ----------

document.addEventListener("DOMContentLoaded", function () {

    const forms =
        document.querySelectorAll(
            "form[data-loading='true']"
        );

    forms.forEach(function (form) {

        form.addEventListener("submit", function () {

            const button =
                form.querySelector(
                    "button[type='submit']"
                );

            if (button) {

                button.disabled = true;

                button.dataset.originalText =
                    button.innerHTML;

                button.innerHTML =
                    "Processing...";

            }

        });

    });

});


// ---------- Password Show / Hide ----------

function togglePassword(inputId) {

    const input =
        document.getElementById(inputId);

    if (!input) {
        return;
    }

    if (input.type === "password") {

        input.type = "text";

    } else {

        input.type = "password";

    }
}


// ---------- Progress Validation ----------

function validateProgress(input) {

    let value =
        parseInt(input.value);

    if (isNaN(value)) {
        input.value = 0;
        return;
    }

    if (value < 0) {
        input.value = 0;
    }

    if (value > 100) {
        input.value = 100;
    }
}


// ---------- Percentage Calculator ----------

function calculatePercentage(
    scoreId,
    totalId,
    percentageId
) {

    const score =
        parseFloat(
            document.getElementById(scoreId)?.value
        );

    const total =
        parseFloat(
            document.getElementById(totalId)?.value
        );

    const percentageField =
        document.getElementById(percentageId);

    if (!percentageField) {
        return;
    }

    if (
        isNaN(score) ||
        isNaN(total) ||
        total <= 0
    ) {
        percentageField.value = "";
        return;
    }

    const percentage =
        (score / total) * 100;

    percentageField.value =
        percentage.toFixed(2);
}


// ---------- Status Badge Helper ----------

function setStatusBadge(elementId, status) {

    const element =
        document.getElementById(elementId);

    if (!element) {
        return;
    }

    element.className = "badge";

    if (
        status.toLowerCase() === "active" ||
        status.toLowerCase() === "pass" ||
        status.toLowerCase() === "completed"
    ) {

        element.classList.add("bg-success");

    } else if (
        status.toLowerCase() === "pending" ||
        status.toLowerCase() === "in progress"
    ) {

        element.classList.add(
            "bg-warning",
            "text-dark"
        );

    } else {

        element.classList.add("bg-danger");

    }

    element.textContent = status;
}