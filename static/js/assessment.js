// ==========================================
// SkillBridge - Assessment JavaScript
// ==========================================


// ---------- Prevent Multiple Submission ----------

document.addEventListener("DOMContentLoaded", function () {

    const forms =
        document.querySelectorAll(
            ".assessment-form"
        );

    forms.forEach(function (form) {

        form.addEventListener("submit", function () {

            const submitButton =
                form.querySelector(
                    "button[type='submit']"
                );

            if (submitButton) {

                submitButton.disabled = true;

                submitButton.innerHTML =
                    "Submitting...";

            }

        });

    });

});


// ---------- Confirm Assessment Submit ----------

function confirmAssessmentSubmit() {

    return confirm(
        "Are you sure you want to submit your assessment? You cannot change your answers after submission."
    );
}


// ---------- Question Navigation ----------

function showQuestion(questionNumber) {

    const questions =
        document.querySelectorAll(
            ".assessment-question"
        );

    questions.forEach(function (question) {
        question.style.display = "none";
    });

    const currentQuestion =
        document.getElementById(
            "question-" + questionNumber
        );

    if (currentQuestion) {
        currentQuestion.style.display = "block";
    }

    updateQuestionNumber(questionNumber);
}


// ---------- Update Question Number ----------

function updateQuestionNumber(number) {

    const counter =
        document.getElementById(
            "questionCounter"
        );

    if (counter) {

        const total =
            document.querySelectorAll(
                ".assessment-question"
            ).length;

        counter.textContent =
            "Question " + number + " of " + total;
    }
}


// ---------- Next Question ----------

function nextQuestion(currentNumber) {

    const questions =
        document.querySelectorAll(
            ".assessment-question"
        );

    const nextNumber =
        currentNumber + 1;

    if (nextNumber <= questions.length) {

        showQuestion(nextNumber);

    }

}


// ---------- Previous Question ----------

function previousQuestion(currentNumber) {

    const previousNumber =
        currentNumber - 1;

    if (previousNumber >= 1) {

        showQuestion(previousNumber);

    }

}


// ---------- Progress Bar ----------

function updateAssessmentProgress(currentNumber) {

    const questions =
        document.querySelectorAll(
            ".assessment-question"
        );

    const total =
        questions.length;

    const progressBar =
        document.getElementById(
            "assessmentProgress"
        );

    if (!progressBar || total === 0) {
        return;
    }

    const percentage =
        (currentNumber / total) * 100;

    progressBar.style.width =
        percentage + "%";

    progressBar.setAttribute(
        "aria-valuenow",
        percentage
    );
}


// ---------- Count Answered Questions ----------

function countAnsweredQuestions() {

    const questions =
        document.querySelectorAll(
            ".assessment-question"
        );

    let answered = 0;

    questions.forEach(function (question) {

        const selected =
            question.querySelector(
                "input[type='radio']:checked"
            );

        if (selected) {
            answered++;
        }

    });

    const counter =
        document.getElementById(
            "answeredCounter"
        );

    if (counter) {

        counter.textContent =
            answered +
            " / " +
            questions.length +
            " answered";

    }

    return answered;
}


// ---------- Listen for Answer Changes ----------

document.addEventListener("DOMContentLoaded", function () {

    const radioButtons =
        document.querySelectorAll(
            "input[type='radio']"
        );

    radioButtons.forEach(function (radio) {

        radio.addEventListener(
            "change",
            function () {

                countAnsweredQuestions();

            }
        );

    });

});


// ---------- Initialize Assessment ----------

document.addEventListener("DOMContentLoaded", function () {

    const questions =
        document.querySelectorAll(
            ".assessment-question"
        );

    if (questions.length > 0) {

        showQuestion(1);

        updateAssessmentProgress(1);

        countAnsweredQuestions();

    }

});