using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class MessageParser : MonoBehaviour
{
    public Udpnetwork UDP;
    public event Action<string, string[]> OnMessageParsed;

    private void FixedUpdate()
    {
        ParsingMsg();
    }

    void ParsingMsg()
    {
        if (UDP == null) return;

        while (UDP.ex1.Count > 0)
        {
            try
            {
                string msg = UDP.ex1.Dequeue();
                string[] tokens = msg.Split(',');
                OnMessageParsed?.Invoke(msg, tokens);
            }
            catch (Exception e)
            {
                //continue;
                UDP.ex1.Clear();
                Debug.LogError(e);
            }
        }
    }
}