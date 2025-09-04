using UnityEngine;

public class ClickToMove : MonoBehaviour
{
    public Camera mainCamera;
    public float moveSpeed = 5f;      // 이동 속도
    public float rotateSpeed = 1f;  // 회전 감도

    private Vector3 targetPosition;
    private bool isMoving = false;

    private bool isDragging = false;
    private bool movedDuringDrag = false;
    private Vector2 lastMousePosition;

    void Start()
    {
        if (mainCamera == null)
        {
            mainCamera = Camera.main;
        }
        targetPosition = transform.position;
    }

    void Update()
    {
        HandleDragRotation();   // 회전
        HandleClickMove();      // 이동
        HandleMoveToTarget();   // 타겟 위치까지 이동
    }

    void HandleDragRotation()
    {
        if (Input.GetMouseButtonDown(0))
        {
            lastMousePosition = Input.mousePosition;
            isDragging = true;
            movedDuringDrag = false;
        }
        else if (Input.GetMouseButton(0) && isDragging)
        {
            Vector2 currentPosition = Input.mousePosition;
            Vector2 delta = currentPosition - lastMousePosition;

            if (delta.magnitude > 1f)
            {
                movedDuringDrag = true;

                float rotationAmount = -delta.x * rotateSpeed;
                transform.Rotate(Vector3.up, rotationAmount, Space.World);
            }

            lastMousePosition = currentPosition;
        }
        else if (Input.GetMouseButtonUp(0))
        {
            isDragging = false;
        }
    }

    void HandleClickMove()
    {
        if (Input.GetMouseButtonUp(0) && !movedDuringDrag)
        {
            Ray ray = mainCamera.ScreenPointToRay(Input.mousePosition);
            if (Physics.Raycast(ray, out RaycastHit hit))
            {
                targetPosition = hit.point;
                isMoving = true;
            }
        }
    }

    void HandleMoveToTarget()
    {
        if (isMoving)
        {
            transform.position = Vector3.MoveTowards(transform.position, targetPosition, moveSpeed * Time.deltaTime);

            if (Vector3.Distance(transform.position, targetPosition) < 0.01f)
            {
                isMoving = false;
            }
        }
    }
}
