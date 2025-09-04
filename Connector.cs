using System.Collections;
using System.Collections.Generic;
using Unity.VisualScripting;
using UnityEngine;

public class Connector : MonoBehaviour
{
    public int count = 0;
    public bool activate;
    public bool rotateMode;

    public MecanumTargetFollower8WayHysteresis MTS;

    public UDP UDP;


    [Range(0f, 5f)]
    public float ratio = 1f;

    [Range(0f, 1f)]
    public float offset = 0.6f;

    public float moveintensity = 0.9f;

    [Range(0f, 1f)]
    public float clamp = 0.3f;
    public float input_m1;
    public float input_m2;
    public float input_m3;
    public float input_m4;

    public float output_m1;
    public float output_m2;
    public float output_m3;
    public float output_m4;

    // Start is called before the first frame update
    void Start()
    {
        Application.targetFrameRate = 50;
    }

    // Update is called once per frame
    void Update()
    {
        count += 1;
        if (MTS != null)
        {

            if (MTS.isRotateMode == true)
            {
                input_m1 = MTS.wheelSpeedFL;
                input_m2 = MTS.wheelSpeedFR;
                input_m3 = MTS.wheelSpeedRL;
                input_m4 = MTS.wheelSpeedRR;

                output_m1 = input_m1 * ratio;
                output_m2 = input_m2 * ratio;
                output_m3 = input_m3 * ratio;
                output_m4 = input_m4 * ratio;


                output_m1 = Mathf.Clamp(output_m1, -clamp, clamp);
                output_m2 = Mathf.Clamp(output_m2, -clamp, clamp);
                output_m3 = Mathf.Clamp(output_m3, -clamp, clamp);
                output_m4 = Mathf.Clamp(output_m4, -clamp, clamp);

                if (output_m1 > 0f)
                {
                    output_m1 += offset;
                }

                else
                {
                    output_m1 -= offset;
                }

                if (output_m2 > 0f)
                {
                    output_m2 += offset;
                }

                else
                {
                    output_m2 -= offset;
                }

                if (output_m3 > 0f)
                {
                    output_m3 += offset;
                }

                else
                {
                    output_m3 -= offset;
                }

                if (output_m4 > 0f)
                {
                    output_m4 += offset;
                }

                else
                {
                    output_m4 -= offset;
                }
            }
            else if (MTS.isRotateMode == false)
            {
                input_m1 = MTS.wheelSpeedFL;
                input_m2 = MTS.wheelSpeedFR;
                input_m3 = MTS.wheelSpeedRL;
                input_m4 = MTS.wheelSpeedRR;

                if (input_m1 > 0f)
                {
                    input_m1 = moveintensity;
                }
                else if (input_m1 < 0f)
                {
                    input_m1 = -moveintensity;
                }

                if (input_m2 > 0f)
                {
                    input_m2 = moveintensity;
                }
                else if (input_m2 < 0f)
                {
                    input_m2 = -moveintensity;
                }

                if (input_m3 > 0f)
                {
                    input_m3 = moveintensity;
                }
                else if (input_m3 < 0f)
                {
                    input_m3 = -moveintensity;
                }

                if (input_m4 > 0f)
                {
                    input_m4 = moveintensity;
                }
                else if (input_m4 < 0f)
                {
                    input_m4 = -moveintensity;
                }

                output_m1 = -input_m1;
                output_m2 = -input_m2;
                output_m3 = -input_m3;
                output_m4 = -input_m4;
            }
        }

        if (Input.GetKeyDown(KeyCode.Space))
        {
            activate = !activate;
        }

        Cmd();
    }

    void Cmd()
    {
        if (UDP != null)
        {
            if(activate == true)
            {
                UDP.Sendmsg($"{output_m1},{output_m2},{output_m3},{output_m4}");
            }

            else
            {
                UDP.Sendmsg($"0,0,0,0");
            }
        }
    }
}
