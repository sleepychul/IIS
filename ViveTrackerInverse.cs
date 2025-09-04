using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class ViveTrackerInverse : MonoBehaviour
{
    public enum Mode
    {
        None = 0,
        pivot1Inverse = 1,
        pivot1and2Forward = 2,
    }

    [Header("Mode")]
    public Mode mode = Mode.pivot1Inverse;

    [Header("Visualization")]
    public bool visualize;
    public Transform[] visualizer;

    [Header("Messaging")]
    public MessageParser messages;

    [Header("Transforms")]
    public Transform pivotTracker;   // Unity에서 트래커1을 둘 기준 포즈 (base)
    public Transform tracker2;
    public Transform target;         // pivot 입장에서의 Lighthouse 원점/축을 표시할 오브젝트

    [Header("Trackers (IDs)")]
    public int myTracker1 = 0;
    public int myTracker2 = 1;

    [Header("Debug (Lighthouse raw pose)")]
    public Vector3 originalPos1;
    public Quaternion originalRot1;
    public Vector3 originalPos2;
    public Quaternion originalRot2;

    // 수신 플래그
    private bool hasTracker1 = false;
    private bool hasTracker2 = false;

    // 역변환 결과(프레임 단위)
    [Header("Computed (pivot 기준 LH origin/axes, per-frame)")]
    public Vector3 lhOriginPosU;     // Unity 공간에서의 (이번 프레임) LH 원점
    public Quaternion lhOriginRotU;  // Unity 공간에서의 (이번 프레임) LH 좌표축 회전

    // 평균값(캘리브레이션 결과)
    [Header("Calibration / Averaging")]
    public bool autoStartCalibrationOnPlay = false;
    public bool useAveraged = false;         // true면 평균 결과로 표시/사용
    public float sampleDuration = 5.0f;      // 샘플링 시간(초)
    public KeyCode calibrationToggleKey = KeyCode.C;

    public Vector3 avgLhOriginPosU;         // 평균 위치
    public Quaternion avgLhOriginRotU;       // 평균 회전
    private bool hasAveraged = false;

    private bool isCalibrating = false;
    private float calibStartTime = 0f;
    private List<Vector3> posSamples = new List<Vector3>(512);
    private List<Quaternion> rotSamples = new List<Quaternion>(512);

    // 캐시
    private Vector3 basePos;
    private Quaternion baseRot;

    void Start()
    {
        if (messages != null) messages.OnMessageParsed += OnMessageReceived;
        else Debug.LogError("ViveTrackerManager (messages) is not assigned!");

        if (autoStartCalibrationOnPlay) BeginCalibration();
    }

    void OnDestroy()
    {
        if (messages != null) messages.OnMessageParsed -= OnMessageReceived;
    }

    void Update()
    {
        // 키로 캘리브레이션 토글
        if (calibrationToggleKey != KeyCode.None && Input.GetKeyDown(calibrationToggleKey))
        {
            if (!isCalibrating) BeginCalibration();
            else CancelCalibration(); // 중간 취소
        }

        if (mode == Mode.None) return;

        if (mode == Mode.pivot1Inverse)
        {
            UpdatePositionRotation();
            // 캘리브레이션 수집 중이면 샘플 추가
            if (isCalibrating) CollectSample();
            ApplyPositionRotation();
        }
        else if (mode == Mode.pivot1and2Forward)
        {
            Forwarding();
        }
    }

    void OnMessageReceived(string msg, string[] tokens)
    {
        if (tokens.Length < 8) return;
        if (!int.TryParse(tokens[0], out int trackerID)) return;

        // id, x, y, z, qx, qy, qz, qw
        if (trackerID == myTracker1)
        {
            if (float.TryParse(tokens[1], out float x) &&
                float.TryParse(tokens[2], out float y) &&
                float.TryParse(tokens[3], out float z) &&
                float.TryParse(tokens[4], out float qx) &&
                float.TryParse(tokens[5], out float qy) &&
                float.TryParse(tokens[6], out float qz) &&
                float.TryParse(tokens[7], out float qw))
            {
                originalPos1 = new Vector3(x, y, z);
                originalRot1 = new Quaternion(qx, qy, qz, qw);
                hasTracker1 = true;
            }
        }
        else if (trackerID == myTracker2)
        {
            if (float.TryParse(tokens[1], out float x) &&
                float.TryParse(tokens[2], out float y) &&
                float.TryParse(tokens[3], out float z) &&
                float.TryParse(tokens[4], out float qx) &&
                float.TryParse(tokens[5], out float qy) &&
                float.TryParse(tokens[6], out float qz) &&
                float.TryParse(tokens[7], out float qw))
            {
                originalPos2 = new Vector3(x, y, z);
                originalRot2 = new Quaternion(qx, qy, qz, qw);
                hasTracker2 = true;
            }
        }
    }

    // ----------------------------------------------------------
    // pivot1Inverse: tracker1의 Lighthouse 포즈를 역변환하여
    // pivot 기준으로 본 Lighthouse 원점/축(lhOriginPosU/RotU)을 구함
    // ----------------------------------------------------------
    void UpdatePositionRotation()
    {
        if (!hasTracker1 || pivotTracker == null) return;

        Quaternion R1 = NormalizeSafe(originalRot1);
        Vector3 P1 = originalPos1;

        basePos = pivotTracker.position;
        baseRot = pivotTracker.rotation;

        // Lighthouse 원점의 Unity 좌표: pU = basePos - baseRot * ( R1^-1 * P1 )
        lhOriginPosU = basePos - (baseRot * (Quaternion.Inverse(R1) * P1));

        // Lighthouse 좌표축의 Unity 회전: rU = baseRot * ( R1^-1 )
        lhOriginRotU = Quaternion.Normalize(baseRot * Quaternion.Inverse(R1));
    }

    void ApplyPositionRotation()
    {
        if (target == null) return;

        // 평균 결과를 쓰기로 했고 준비되어 있으면 평균값, 아니면 현재 프레임 값
        Vector3 pos = (useAveraged && hasAveraged) ? avgLhOriginPosU : lhOriginPosU;
        Quaternion rot = (useAveraged && hasAveraged) ? avgLhOriginRotU : lhOriginRotU;

        target.position = pos;
        target.rotation = rot;

        if (visualize && visualizer != null)
        {
            foreach (var t in visualizer)
            {
                if (t == null) continue;
                t.position = pos;
                t.rotation = rot;
            }
        }
    }

    // ----------------------------------------------------------
    // 캘리브레이션(샘플링 → 평균화)
    // ----------------------------------------------------------
    public void BeginCalibration()
    {
        if (isCalibrating) return;
        if (!hasTracker1)
        {
            Debug.LogWarning("BeginCalibration: tracker1 pose not available yet.");
            return;
        }

        isCalibrating = true;
        calibStartTime = Time.time;
        posSamples.Clear();
        rotSamples.Clear();
        hasAveraged = false;
        Debug.Log($"[Calibration] started for {sampleDuration:F2}s");
    }

    public void CancelCalibration()
    {
        if (!isCalibrating) return;
        isCalibrating = false;
        posSamples.Clear();
        rotSamples.Clear();
        Debug.Log("[Calibration] canceled");
    }

    private void CollectSample()
    {
        // UpdatePositionRotation() 이후에 호출됨을 가정
        posSamples.Add(lhOriginPosU);
        rotSamples.Add(lhOriginRotU);

        // 기간 종료 시 평균 계산
        if (Time.time - calibStartTime >= sampleDuration)
        {
            isCalibrating = false;

            if (posSamples.Count > 0)
            {
                avgLhOriginPosU = AverageVector(posSamples);
            }
            else
            {
                avgLhOriginPosU = lhOriginPosU;
            }

            if (rotSamples.Count > 0)
            {
                avgLhOriginRotU = AverageQuaternion(rotSamples);
            }
            else
            {
                avgLhOriginRotU = lhOriginRotU;
            }

            hasAveraged = true;
            useAveraged = true; // 자동으로 평균값 사용 시작(원하면 꺼도 됨)
            Debug.Log($"[Calibration] done. samples={posSamples.Count} | useAveraged={useAveraged}");
        }
    }

    // ----------------------------------------------------------
    // Forwarding: target 포즈를 기준으로 tracker1/2를 전방향 변환(옵션)
    // ----------------------------------------------------------
    void Forwarding()
    {
        if (target == null) return;

        Vector3 basePosF = target.position;
        Quaternion baseRotF = target.rotation;

        if (hasTracker1)
        {
            // pU = basePosF + baseRotF * pL
            pivotTracker.position = basePosF + baseRotF * originalPos1;
            pivotTracker.rotation = baseRotF * originalRot1;
        }

        if (hasTracker2 && tracker2 != null)
        {
            tracker2.position = basePosF + baseRotF * originalPos2;
            tracker2.rotation = baseRotF * originalRot2;
        }
    }

    // --- helpers ---

    private static Quaternion NormalizeSafe(Quaternion q)
    {
        float mag = Mathf.Sqrt(q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w);
        if (mag < 1e-6f) return Quaternion.identity;
        return new Quaternion(q.x / mag, q.y / mag, q.z / mag, q.w / mag);
    }

    private static Vector3 AverageVector(List<Vector3> vs)
    {
        if (vs == null || vs.Count == 0) return Vector3.zero;
        Vector3 sum = Vector3.zero;
        for (int i = 0; i < vs.Count; ++i) sum += vs[i];
        return sum / vs.Count;
    }

    // 부호 보정 + 정규화 기반 퀘터니언 평균 (간단·안정)
    private static Quaternion AverageQuaternion(List<Quaternion> qs)
    {
        if (qs == null || qs.Count == 0) return Quaternion.identity;

        // 기준 퀘터니언
        Quaternion q0 = NormalizeSafe(qs[0]);
        Vector4 acc = new Vector4(q0.x, q0.y, q0.z, q0.w);

        for (int i = 1; i < qs.Count; ++i)
        {
            Quaternion qi = NormalizeSafe(qs[i]);
            // antipodal 보정: dot < 0이면 부호 반전
            if (Quaternion.Dot(q0, qi) < 0f)
                qi = new Quaternion(-qi.x, -qi.y, -qi.z, -qi.w);

            acc.x += qi.x;
            acc.y += qi.y;
            acc.z += qi.z;
            acc.w += qi.w;
        }

        // 정규화
        float mag = Mathf.Sqrt(acc.x * acc.x + acc.y * acc.y + acc.z * acc.z + acc.w * acc.w);
        if (mag < 1e-6f) return q0;
        return new Quaternion(acc.x / mag, acc.y / mag, acc.z / mag, acc.w / mag);
    }
}


//using System.Collections;
//using System.Collections.Generic;
//using UnityEngine;

//public class ViveTrackerInverse : MonoBehaviour
//{

//    public enum Mode
//    {
//        None = 0,
//        pivot1Inverse = 1,
//        pivot1and2Forward = 2,
//    }

//    public Mode mode;
//    public bool visualize;
//    public Transform[] visualizer;

//    public MessageParser messages;

//    public Transform pivotTracker;   // 기준 포즈(= Lighthouse→Unity 매핑의 base)
//    public Transform tracker2;
//    public Transform target;  // pivot 입장에서의 Lighthouse 원점을 표시할 오브젝트


//    public int myTracker1;
//    public int myTracker2;

//    [Header("Debug (수신된 Lighthouse 포즈)")]
//    public Vector3 originalPos1;
//    public Quaternion originalRot1;

//    [Header("Debug (수신된 Lighthouse 포즈)")]
//    public Vector3 originalPos2;
//    public Quaternion originalRot2;

//    // 내부 상태
//    private bool hasTracker1 = false;
//    private bool hasTracker2 = false;

//    // 계산된 값(읽기용)
//    [Header("Computed (pivot에서 본 Lighthouse 원점/회전)")]
//    public Vector3 lhOriginPosU;     // Unity 공간에서의 LH 원점
//    public Quaternion lhOriginRotU;  // Unity 공간에서의 LH 좌표축 회전

//    // 캐시용
//    private Vector3 basePos;
//    private Quaternion baseRot;

//    void Start()
//    {
//        if (messages != null)
//        {
//            messages.OnMessageParsed += OnMessageReceived;
//        }
//        else
//        {
//            Debug.LogError("ViveTrackerManager is not assigned!");
//        }
//    }

//    void OnDestroy()
//    {
//        if (messages != null)
//        {
//            messages.OnMessageParsed -= OnMessageReceived;
//        }
//    }

//    void Update()
//    {
//        if (mode == Mode.None)
//        {
//            return;
//        }

//        else if(mode == Mode.pivot1Inverse)
//        {
//            UpdatePositionRotation();
//            ApplyPositionRotation();
//        }

//        else if (mode == Mode.pivot1and2Forward)
//        {
//            Forwarding();
//        }

//    }


//    void OnMessageReceived(string msg, string[] tokens)
//    {
//        if (tokens.Length < 8) return;
//        if (!int.TryParse(tokens[0], out int trackerID)) return;

//        if (trackerID == myTracker1)
//        {
//            if (float.TryParse(tokens[1], out float x) &&
//                float.TryParse(tokens[2], out float y) &&
//                float.TryParse(tokens[3], out float z) &&
//                float.TryParse(tokens[4], out float qx) &&
//                float.TryParse(tokens[5], out float qy) &&
//                float.TryParse(tokens[6], out float qz) &&
//                float.TryParse(tokens[7], out float qw))
//            {
//                originalPos1 = new Vector3(x, y, z);
//                originalRot1 = new Quaternion(qx, qy, qz, qw);
//                hasTracker1 = true;
//            }
//        }

//        else if (trackerID == myTracker2)
//        {
//            if (float.TryParse(tokens[1], out float x) &&
//                float.TryParse(tokens[2], out float y) &&
//                float.TryParse(tokens[3], out float z) &&
//                float.TryParse(tokens[4], out float qx) &&
//                float.TryParse(tokens[5], out float qy) &&
//                float.TryParse(tokens[6], out float qz) &&
//                float.TryParse(tokens[7], out float qw))
//            {
//                originalPos2 = new Vector3(x, y, z);
//                originalRot2 = new Quaternion(qx, qy, qz, qw);
//                hasTracker2 = true;
//            }
//        }
//    }

//    void UpdatePositionRotation()
//    {
//        if (!hasTracker1) return;
//        if (pivotTracker == null) return;

//        // 방어적 정규화
//        Quaternion R1 = NormalizeSafe(originalRot1);
//        Vector3 P1 = originalPos1;

//        // pivot 포즈
//        basePos = pivotTracker.position;
//        baseRot = pivotTracker.rotation;

//        // --- 역변환 핵심 ---
//        // Lighthouse 원점의 Unity 좌표
//        lhOriginPosU = basePos - (baseRot * (Quaternion.Inverse(R1) * P1));

//        // Lighthouse 좌표축의 Unity 회전
//        lhOriginRotU = Quaternion.Normalize(baseRot * Quaternion.Inverse(R1));
//    }

//    void ApplyPositionRotation()
//    {
//        if (target == null) return;

//        // target을 "pivot 입장에서 본 Lighthouse 좌표계"로 배치
//        target.position = lhOriginPosU;
//        target.rotation = lhOriginRotU;

//        // (옵션) 추가 시각화
//        if (visualize && visualizer != null)
//        {
//            foreach (var t in visualizer)
//            {
//                if (t == null) continue;
//                t.position = lhOriginPosU;
//                t.rotation = lhOriginRotU;
//            }
//        }
//    }

//    // --- helper ---
//    private static Quaternion NormalizeSafe(Quaternion q)
//    {
//        float mag = Mathf.Sqrt(q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w);
//        if (mag < 1e-6f) return Quaternion.identity;
//        return new Quaternion(q.x / mag, q.y / mag, q.z / mag, q.w / mag);
//    }

//    void Forwarding()
//    {
//        if(hasTracker1 == true)
//        {
//            // 예측된 베이스 포즈를 로컬 변수에 담아두면 가독성이 좋아집니다.
//            Vector3 basePos = target.position;
//            Quaternion baseRot = target.rotation;

//            // tracker1
//            pivotTracker.position = basePos + baseRot * originalPos1;
//            pivotTracker.rotation = baseRot * originalRot1;
//        }

//        if (hasTracker2 == true)
//        {
//            // 예측된 베이스 포즈를 로컬 변수에 담아두면 가독성이 좋아집니다.
//            Vector3 basePos = target.position;
//            Quaternion baseRot = target.rotation;

//            // tracker1
//            tracker2.position = basePos + baseRot * originalPos2;
//            tracker2.rotation = baseRot * originalRot2;
//        }
//    }
//}
