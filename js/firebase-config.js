/**
 * Firebase 설정
 * 환경 변수는 js/env.js에서 로드됩니다.
 * env.js 파일이 없으면 로컬 모드로 동작합니다.
 */

// ENV가 정의되어 있는지 확인 (env.js 로드 여부)
const firebaseConfig = (typeof ENV !== 'undefined') ? {
    apiKey: ENV.FIREBASE_API_KEY,
    authDomain: ENV.FIREBASE_AUTH_DOMAIN,
    projectId: ENV.FIREBASE_PROJECT_ID,
    storageBucket: ENV.FIREBASE_STORAGE_BUCKET,
    messagingSenderId: ENV.FIREBASE_MESSAGING_SENDER_ID,
    appId: ENV.FIREBASE_APP_ID,
    measurementId: ENV.FIREBASE_MEASUREMENT_ID
} : {
    apiKey: "YOUR_API_KEY"
};

// Firebase 초기화 여부 플래그
let firebaseInitialized = false;
let db = null;

/**
 * Firebase 초기화
 */
function initFirebase() {
    // 이미 설정되어 있지 않으면 초기화하지 않음
    if (firebaseConfig.apiKey === "YOUR_API_KEY") {
        console.log("⚠️ Firebase가 설정되지 않았습니다. 리액션/투표 기능이 로컬 모드로 동작합니다.");
        return false;
    }
    
    try {
        firebase.initializeApp(firebaseConfig);
        db = firebase.firestore();
        firebaseInitialized = true;
        console.log("✅ Firebase 초기화 완료");
        return true;
    } catch (error) {
        console.error("Firebase 초기화 실패:", error);
        return false;
    }
}

// 페이지 로드 시 Firebase 초기화 시도
initFirebase();
